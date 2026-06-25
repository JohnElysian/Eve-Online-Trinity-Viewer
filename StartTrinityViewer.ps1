param(
  [int]$TypeID = 587,
  [string]$ClientPath = "",
  [int]$Width = 1280,
  [int]$Height = 820,
  [string]$Mode = "material",
  [switch]$ResetClient,
  [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"

$ToolRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RuntimeRoot = Join-Path $ToolRoot "runtime"
$SettingsPath = Join-Path $RuntimeRoot "settings.json"
$CatalogPath = Join-Path $RuntimeRoot "catalog.json"
$BundledCatalogPath = Join-Path $ToolRoot "catalog\catalog.json"
$BundledCatalogGzipPath = Join-Path $ToolRoot "catalog\catalog.json.gz"
$CatalogDownloadUrl = "https://raw.githubusercontent.com/JohnElysian/Eve-Online-Trinity-Viewer/main/catalog/catalog.json.gz"
$ViewerPath = Join-Path $ToolRoot "trinity_live_viewer.py"
$PythonHome = Join-Path $ToolRoot "python27"
$BuilderPath = Join-Path $ToolRoot "build_standalone_catalog.js"

function Write-Stage($message) {
  Write-Host "[Jessica] $message"
}

function Quote-Argument($value) {
  $text = [string]$value
  if ($text.Length -eq 0) {
    return '""'
  }
  if ($text -match '[\s"]') {
    return '"' + ($text -replace '"', '\"') + '"'
  }
  return $text
}

function Read-Settings {
  if (-not (Test-Path -LiteralPath $SettingsPath)) {
    return [pscustomobject]@{}
  }
  try {
    return Get-Content -LiteralPath $SettingsPath -Raw | ConvertFrom-Json
  } catch {
    return [pscustomobject]@{}
  }
}

function Save-Settings($settings) {
  New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
  $settings | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SettingsPath -Encoding UTF8
}

function Test-CatalogUsable($path) {
  if (-not (Test-Path -LiteralPath $path)) {
    return $false
  }
  try {
    $catalog = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    $assets = @($catalog.assets)
    if ($assets.Count -le 0) {
      return $false
    }
    foreach ($asset in ($assets | Select-Object -First 64)) {
      if ($asset.dna) {
        return $true
      }
    }
    return $false
  } catch {
    return $false
  }
}

function Expand-GzipFile($sourcePath, $destinationPath) {
  New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($destinationPath)) | Out-Null
  $input = [System.IO.File]::OpenRead($sourcePath)
  try {
    $gzip = New-Object System.IO.Compression.GzipStream($input, [System.IO.Compression.CompressionMode]::Decompress)
    try {
      $output = [System.IO.File]::Create($destinationPath)
      try {
        $gzip.CopyTo($output)
      } finally {
        $output.Dispose()
      }
    } finally {
      $gzip.Dispose()
    }
  } finally {
    $input.Dispose()
  }
}

function Restore-BundledCatalog {
  if (Test-Path -LiteralPath $BundledCatalogPath) {
    Write-Stage "Restoring bundled catalogue..."
    New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
    Copy-Item -LiteralPath $BundledCatalogPath -Destination $CatalogPath -Force
    return (Test-CatalogUsable $CatalogPath)
  }
  if (Test-Path -LiteralPath $BundledCatalogGzipPath) {
    Write-Stage "Restoring bundled catalogue..."
    Expand-GzipFile $BundledCatalogGzipPath $CatalogPath
    return (Test-CatalogUsable $CatalogPath)
  }
  return $false
}

function Download-Catalog {
  $downloadPath = Join-Path $RuntimeRoot "catalog.download.json.gz"
  try {
    Write-Stage "Downloading viewer metadata catalogue..."
    New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
    Invoke-WebRequest -Uri $CatalogDownloadUrl -OutFile $downloadPath -UseBasicParsing
    Expand-GzipFile $downloadPath $CatalogPath
    return (Test-CatalogUsable $CatalogPath)
  } catch {
    Write-Stage "Catalogue download was not available: $($_.Exception.Message)"
    return $false
  } finally {
    Remove-Item -LiteralPath $downloadPath -Force -ErrorAction SilentlyContinue
  }
}

function Test-InternalCatalogBuildData {
  $repoRoot = [System.IO.Path]::GetFullPath((Join-Path $ToolRoot "..\.."))
  return (
    (Test-Path -LiteralPath (Join-Path $repoRoot "tools\ClientSDE\exports")) -and
    (Test-Path -LiteralPath (Join-Path $repoRoot "server\src\newDatabase\data\itemTypes\data.json")) -and
    (Test-Path -LiteralPath (Join-Path $repoRoot "server\src\newDatabase\data\shipTypes\data.json"))
  )
}

function Test-EveClientRoot($path) {
  if (-not $path) {
    return $false
  }
  $resolved = [System.IO.Path]::GetFullPath($path)
  return (
    (Test-Path -LiteralPath (Join-Path $resolved "bin64\exefile.exe")) -and
    (Test-Path -LiteralPath (Join-Path $resolved "resfileindex.txt"))
  )
}

function Resolve-ResFilesRoot($clientRoot) {
  $candidates = @(
    (Join-Path $clientRoot "..\ResFiles"),
    (Join-Path $clientRoot "ResFiles"),
    (Join-Path $clientRoot "..\SharedCache\ResFiles"),
    (Join-Path $clientRoot "SharedCache\ResFiles")
  )
  foreach ($candidate in $candidates) {
    $full = [System.IO.Path]::GetFullPath($candidate)
    if (Test-Path -LiteralPath $full) {
      return $full
    }
  }
  return [System.IO.Path]::GetFullPath((Join-Path $clientRoot "..\ResFiles"))
}

function Resolve-EveClientRoot($path) {
  if (-not $path) {
    return $null
  }
  $base = [System.IO.Path]::GetFullPath($path)
  $candidates = @(
    $base,
    (Join-Path $base "tq"),
    (Join-Path $base "sisi"),
    (Join-Path $base "tranquility")
  )
  foreach ($candidate in $candidates) {
    $full = [System.IO.Path]::GetFullPath($candidate)
    if (Test-EveClientRoot $full) {
      return [pscustomobject]@{
        ClientRoot = $full
        Exefile = Join-Path $full "bin64\exefile.exe"
        ResFilesRoot = Resolve-ResFilesRoot $full
      }
    }
  }
  return $null
}

function Find-DefaultClient {
  $settings = Read-Settings
  $paths = @()
  if ($ClientPath) {
    $paths += $ClientPath
  }
  if ($env:ELYSIAN_JESSICA_EVE_CLIENT) {
    $paths += $env:ELYSIAN_JESSICA_EVE_CLIENT
  }
  if (-not $ResetClient -and $settings.eveClientRoot) {
    $paths += [string]$settings.eveClientRoot
  }
  $paths += @(
    (Join-Path $ToolRoot "client"),
    (Join-Path $ToolRoot "..\..\client\EVE\tq"),
    "C:\CCP\EVE\tq",
    "C:\CCP\EVE\sisi",
    "C:\CCP\EVE",
    "C:\Program Files\CCP\EVE\tq",
    "C:\Program Files (x86)\CCP\EVE\tq"
  )
  foreach ($path in $paths) {
    $resolved = Resolve-EveClientRoot $path
    if ($resolved) {
      return $resolved
    }
  }
  return $null
}

function Select-ClientFolder {
  Add-Type -AssemblyName System.Windows.Forms
  $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
  $dialog.Description = "Select your EVE client folder. Choose the folder containing tq, or the tq folder itself."
  $dialog.ShowNewFolderButton = $false
  if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
    throw "No EVE client folder selected."
  }
  $resolved = Resolve-EveClientRoot $dialog.SelectedPath
  if (-not $resolved) {
    throw "Selected folder is not an EVE client root: $($dialog.SelectedPath)"
  }
  return $resolved
}

function Ensure-Python27 {
  if (Test-Path -LiteralPath (Join-Path $PythonHome "Lib\json\__init__.py")) {
    return
  }

  New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
  $repoPython = [System.IO.Path]::GetFullPath((Join-Path $ToolRoot "..\ClientCodeGrabberV2\runtime\python27"))
  if (Test-Path -LiteralPath (Join-Path $repoPython "Lib\json\__init__.py")) {
    Write-Stage "Installing bundled Python 2.7 runtime from repo tools..."
    Copy-Item -LiteralPath $repoPython -Destination $PythonHome -Recurse -Force
    return
  }

  $downloadRoot = Join-Path $RuntimeRoot "prereq-download"
  $extractRoot = Join-Path $RuntimeRoot "python27-extract"
  $msiPath = Join-Path $downloadRoot "python-2.7.18.amd64.msi"
  New-Item -ItemType Directory -Force -Path $downloadRoot | Out-Null
  New-Item -ItemType Directory -Force -Path $extractRoot | Out-Null
  if (-not (Test-Path -LiteralPath $msiPath)) {
    Write-Stage "Downloading Python 2.7.18 runtime prerequisite..."
    Invoke-WebRequest -Uri "https://www.python.org/ftp/python/2.7.18/python-2.7.18.amd64.msi" -OutFile $msiPath
  }
  Write-Stage "Extracting Python 2.7 runtime locally..."
  $process = Start-Process -FilePath "msiexec.exe" -ArgumentList @("/a", "`"$msiPath`"", "/qn", "TARGETDIR=`"$extractRoot`"") -Wait -PassThru
  if ($process.ExitCode -ne 0) {
    throw "Python prerequisite extraction failed with code $($process.ExitCode)."
  }
  $candidatePaths = @($extractRoot) + @(
    Get-ChildItem -LiteralPath $extractRoot -Recurse -Directory |
      ForEach-Object { $_.FullName }
  )
  $candidate = $candidatePaths |
    Where-Object { Test-Path -LiteralPath (Join-Path $_ "Lib\json\__init__.py") } |
    Select-Object -First 1
  if (-not $candidate) {
    throw "Python prerequisite extraction completed, but the Python27 runtime was not found."
  }
  Copy-Item -LiteralPath $candidate -Destination $PythonHome -Recurse -Force
}

function Ensure-Catalog($client) {
  if (Test-CatalogUsable $CatalogPath) {
    return
  }

  if (Test-Path -LiteralPath $CatalogPath) {
    Write-Stage "Existing catalogue is missing SOF assets; replacing it..."
    $badPath = Join-Path $RuntimeRoot ("catalog.invalid-{0}.json" -f (Get-Date -Format "yyyyMMdd-HHmmss"))
    Move-Item -LiteralPath $CatalogPath -Destination $badPath -Force
  }

  if (Restore-BundledCatalog) {
    return
  }

  if (Download-Catalog) {
    return
  }

  if (-not (Test-Path -LiteralPath $BuilderPath)) {
    throw "Missing viewer metadata catalogue. Download the release zip or use a source archive that includes catalog\catalog.json.gz."
  }
  if (-not (Test-InternalCatalogBuildData)) {
    throw "Missing viewer metadata catalogue. Normal users do not need Elysian Eve's ClientSDE; download the release zip or keep catalog\catalog.json.gz next to this launcher."
  }
  $node = Get-Command node.exe -ErrorAction SilentlyContinue
  if (-not $node) {
    throw "Missing viewer metadata catalogue and Node.js is not installed for an internal rebuild."
  }
  $logDir = Join-Path $RuntimeRoot "logs"
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
  $stdoutPath = Join-Path $logDir "catalog-build.stdout.txt"
  $stderrPath = Join-Path $logDir "catalog-build.stderr.txt"
  Write-Stage "Preparing local asset catalogue..."
  $builderArguments = @($BuilderPath, "--client-root", $client.ClientRoot, "--output", $CatalogPath) |
    ForEach-Object { Quote-Argument $_ }
  $process = Start-Process `
    -FilePath $node.Source `
    -ArgumentList ($builderArguments -join " ") `
    -WorkingDirectory $ToolRoot `
    -Wait `
    -PassThru `
    -RedirectStandardOutput $stdoutPath `
    -RedirectStandardError $stderrPath
  if ($process.ExitCode -ne 0) {
    throw "Catalogue build failed with code $($process.ExitCode). See $stdoutPath and $stderrPath."
  }
  if (-not (Test-Path -LiteralPath $CatalogPath)) {
    throw "Catalogue build completed, but runtime catalogue was not written: $CatalogPath"
  }
  if (-not (Test-CatalogUsable $CatalogPath)) {
    throw "Catalogue build completed, but catalog.json contains no SOF assets."
  }
}

function Select-Asset($catalog) {
  $assets = @($catalog.assets)
  if ($assets.Count -le 0) {
    throw "catalog.json contains no SOF assets."
  }
  $selected = $assets | Where-Object { [int]$_.typeID -eq $TypeID } | Select-Object -First 1
  if (-not $selected) {
    $selected = $assets | Where-Object { [int]$_.typeID -eq [int]$catalog.selectedTypeID } | Select-Object -First 1
  }
  if (-not $selected) {
    $selected = $assets | Select-Object -First 1
  }
  return $selected
}

New-Item -ItemType Directory -Force -Path $RuntimeRoot | Out-Null
Ensure-Python27

if (-not (Test-Path -LiteralPath $ViewerPath)) {
  throw "Missing viewer script: $ViewerPath"
}

$client = Find-DefaultClient
if (-not $client) {
  $client = Select-ClientFolder
}
Ensure-Catalog $client
Save-Settings ([pscustomobject]@{
  eveClientRoot = $client.ClientRoot
  resFilesRoot = $client.ResFilesRoot
  lastTypeID = $TypeID
  width = $Width
  height = $Height
  mode = $Mode
  updatedAt = (Get-Date).ToString("o")
})

$catalog = Get-Content -LiteralPath $CatalogPath -Raw | ConvertFrom-Json
$asset = Select-Asset $catalog
$logDir = Join-Path $RuntimeRoot "logs"
$commandDir = Join-Path $RuntimeRoot "commands"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
New-Item -ItemType Directory -Force -Path $commandDir | Out-Null
$unixEpoch = Get-Date -Date "1970-01-01T00:00:00Z"
$timestampMs = [int64](((Get-Date).ToUniversalTime() - $unixEpoch).TotalMilliseconds)
$commandPath = Join-Path $commandDir ("commands-{0}-{1}.jsonl" -f $asset.typeID, $timestampMs)
Set-Content -LiteralPath $commandPath -Value "" -Encoding ASCII

Write-Stage "Client: $($client.ClientRoot)"
Write-Stage "ResFiles: $($client.ResFilesRoot)"
Write-Stage "Asset: $($asset.typeID) $($asset.name)"
Write-Stage "Catalogue: $CatalogPath"

if ($ValidateOnly) {
  Write-Stage "Validation complete."
  exit 0
}

$arguments = @(
  "/py",
  $ViewerPath,
  [string]$asset.typeID,
  [string]$asset.dna,
  [string]$asset.radius,
  [string]$Width,
  [string]$Height,
  [string]$Mode,
  $CatalogPath,
  $commandPath,
  "/inherit"
)

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $client.Exefile
$psi.WorkingDirectory = $client.ClientRoot
$psi.UseShellExecute = $false
$psi.Arguments = ($arguments | ForEach-Object { Quote-Argument $_ }) -join " "
$psi.EnvironmentVariables["PYTHONHOME"] = $PythonHome
$psi.EnvironmentVariables["PYTHONPATH"] = Join-Path $PythonHome "Lib"
$psi.EnvironmentVariables["ELYSIAN_JESSICA_RESFILES"] = $client.ResFilesRoot

$process = [System.Diagnostics.Process]::Start($psi)
Write-Stage "Launched native Trinity viewer, PID $($process.Id)."
