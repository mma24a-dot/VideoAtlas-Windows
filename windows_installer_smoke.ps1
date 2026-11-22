param(
  [string]$Installer = 'installer-output\VideoAtlas-Setup-2.4.0.exe',
  [string]$Report = 'installer-output\installer-smoke-report.json'
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path '.').Path
$installerPath = (Resolve-Path $Installer).Path
$reportPath = Join-Path $root $Report
$target = Join-Path $env:TEMP ('VideoAtlas-InstallSmoke-' + [guid]::NewGuid().ToString('N'))
$result = @{ ok = $false; installer = $installerPath; install_directory = $target; checks = @() }
try {
  $process = Start-Process -FilePath $installerPath -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/DIR=' + $target)) -Wait -PassThru
  if ($process.ExitCode -ne 0) { throw "Installer returned $($process.ExitCode)" }
  $exe = Join-Path $target 'VideoAtlas.exe'
  if (-not (Test-Path $exe)) { throw 'Installed VideoAtlas.exe not found' }
  $result.checks += 'installed executable exists'
  $selftest = Join-Path $target 'installed-selftest.json'
  $env:QT_QPA_PLATFORM = 'offscreen'
  $test = Start-Process -FilePath $exe -ArgumentList @('--self-test','--self-test-report',$selftest) -Wait -PassThru
  if ($test.ExitCode -ne 0) { throw "Installed executable self-test failed: $($test.ExitCode)" }
  if (-not (Test-Path $selftest)) { throw 'Installed self-test report missing' }
  $details = Get-Content $selftest -Raw | ConvertFrom-Json
  if (-not $details.ok) { throw 'Installed self-test reported failure' }
  $result.checks += 'installed application self-test passed'
  $result.ok = $true
} catch {
  $result.error = $_.Exception.Message
} finally {
  $result | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $reportPath
  Write-Host ($result | ConvertTo-Json -Depth 5)
  if (Test-Path $target) { Remove-Item -Recurse -Force $target -ErrorAction SilentlyContinue }
}
if (-not $result.ok) { exit 1 }
