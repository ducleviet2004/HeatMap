[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$snapshotDate = "260723"
$snapshotVersion = "geofabrik-vietnam-2026-07-23-osrm-v5.27.1"
$snapshotUrl = "https://download.geofabrik.de/asia/vietnam-$snapshotDate.osm.pbf"
$expectedMd5 = "d1f01d6b9840635ff3b3b5be13dfc516"
$osrmImage = "ghcr.io/project-osrm/osrm-backend:v5.27.1"

$repositoryRoot = Split-Path -Parent $PSScriptRoot
$dataDirectory = Join-Path $repositoryRoot "osrm/data"
$inputFile = Join-Path $dataDirectory "region.osm.pbf"
$partialFile = "$inputFile.partial"
$envFile = Join-Path $repositoryRoot ".env"
$envExample = Join-Path $repositoryRoot ".env.example"

function Assert-Command {
    param([Parameter(Mandatory)][string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Required command '$Name' was not found."
    }
}

function Set-EnvValue {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][string]$Value
    )

    $content = Get-Content -LiteralPath $Path -Raw
    $line = "$Name=$Value"
    $pattern = "(?m)^$([regex]::Escape($Name))=.*$"

    if ($content -match $pattern) {
        $content = [regex]::Replace($content, $pattern, $line)
    }
    else {
        $content = $content.TrimEnd() + [Environment]::NewLine + $line + [Environment]::NewLine
    }

    Set-Content -LiteralPath $Path -Value $content -Encoding utf8 -NoNewline
}

Assert-Command "docker"
Assert-Command "curl.exe"

Push-Location $repositoryRoot
try {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Desktop is not running or is not accessible."
    }

    New-Item -ItemType Directory -Path $dataDirectory -Force | Out-Null

    $inputIsValid = $false
    if (Test-Path -LiteralPath $inputFile) {
        Write-Host "Checking the existing Vietnam snapshot..."
        $actualMd5 = (Get-FileHash -LiteralPath $inputFile -Algorithm MD5).Hash.ToLowerInvariant()
        $inputIsValid = $actualMd5 -eq $expectedMd5
        if (-not $inputIsValid) {
            Write-Warning "Existing region.osm.pbf has checksum $actualMd5; expected $expectedMd5."
        }
    }

    if (-not $inputIsValid) {
        Write-Host "Downloading the pinned Vietnam snapshot..."
        & curl.exe -L --fail --retry 10 --retry-all-errors -C - -o $partialFile $snapshotUrl
        if ($LASTEXITCODE -ne 0) {
            throw "Snapshot download failed. Run the script again to resume it."
        }

        $actualMd5 = (Get-FileHash -LiteralPath $partialFile -Algorithm MD5).Hash.ToLowerInvariant()
        if ($actualMd5 -ne $expectedMd5) {
            throw "Snapshot checksum mismatch: expected $expectedMd5, got $actualMd5."
        }

        Move-Item -LiteralPath $partialFile -Destination $inputFile -Force
        Write-Host "Snapshot checksum verified."
    }
    else {
        Write-Host "Reusing the verified Vietnam snapshot."
    }

    $requiredGraphFiles = @(
        "region.osrm.cells",
        "region.osrm.cell_metrics",
        "region.osrm.ebg",
        "region.osrm.edges",
        "region.osrm.geometry",
        "region.osrm.mldgr",
        "region.osrm.names",
        "region.osrm.partition",
        "region.osrm.properties",
        "region.osrm.ramIndex"
    )
    $graphIsReady = ($requiredGraphFiles | Where-Object {
        -not (Test-Path -LiteralPath (Join-Path $dataDirectory $_))
    }).Count -eq 0

    if ($graphIsReady -and -not $Force) {
        Write-Host "Reusing the existing OSRM graph. Use -Force to rebuild it."
    }
    else {
        $dockerDataPath = (Resolve-Path -LiteralPath $dataDirectory).Path.Replace("\", "/")
        $volumeArgument = "${dockerDataPath}:/data"

        Write-Host "Building the OSRM graph (extract)..."
        & docker run --rm -t -v $volumeArgument $osrmImage osrm-extract -p /opt/car.lua /data/region.osm.pbf
        if ($LASTEXITCODE -ne 0) { throw "osrm-extract failed." }

        Write-Host "Building the OSRM graph (partition)..."
        & docker run --rm -t -v $volumeArgument $osrmImage osrm-partition /data/region.osrm
        if ($LASTEXITCODE -ne 0) { throw "osrm-partition failed." }

        Write-Host "Building the OSRM graph (customize)..."
        & docker run --rm -t -v $volumeArgument $osrmImage osrm-customize /data/region.osrm
        if ($LASTEXITCODE -ne 0) { throw "osrm-customize failed." }
    }

    if (-not (Test-Path -LiteralPath $envFile)) {
        Copy-Item -LiteralPath $envExample -Destination $envFile
    }
    Set-EnvValue -Path $envFile -Name "OSRM_URL" -Value "http://osrm:5000"
    Set-EnvValue -Path $envFile -Name "ROUTING_DATA_VERSION" -Value $snapshotVersion

    Write-Host "Starting the Compose stack with the routing profile..."
    & docker compose --profile routing up --build -d
    if ($LASTEXITCODE -ne 0) {
        throw "Docker Compose failed to start the routing stack."
    }

    Write-Host "Checking OSRM and application readiness..."
    $routeUrl = "http://localhost:5000/route/v1/driving/106.7009,10.7769;106.6953,10.7756?overview=false"
    $routeResponse = (& curl.exe --fail --silent $routeUrl | ConvertFrom-Json)
    if ($routeResponse.code -ne "Ok") {
        throw "OSRM route check did not return Ok."
    }

    $readiness = (& curl.exe --fail --silent "http://localhost:8000/api/v1/health/ready" |
        ConvertFrom-Json)
    if ($readiness.status -ne "healthy" -or $readiness.dependencies.osrm.status -ne "ok") {
        throw "Application readiness check failed."
    }

    Write-Host "OSRM Vietnam is ready. Routing data version: $snapshotVersion"
}
finally {
    Pop-Location
}
