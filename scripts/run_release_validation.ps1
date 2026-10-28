# One diagnostic, then dev-01/dev-02/dev-13 only if it succeeds; at most ten requests.
& {
    $probeRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    $probeSecureKey = $null
    $probePlainKey = $null
    $probeKeyPointer = [IntPtr]::Zero
    $probeStartInfo = $null
    $probeProcess = $null
    try {
        $probeSecureKey = Read-Host 'Nebius API key' -AsSecureString
        $probeKeyPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($probeSecureKey)
        $probePlainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($probeKeyPointer).Trim()
        if ([string]::IsNullOrEmpty($probePlainKey) -or $probePlainKey -match '[^\x21-\x7E]') {
            throw 'Key rejected: use printable ASCII without internal whitespace or control characters.'
        }
        $probeStartInfo = New-Object System.Diagnostics.ProcessStartInfo
        $probeStartInfo.FileName = Join-Path $probeRoot '.venv/Scripts/python.exe'
        $probeStartInfo.Arguments = '-B scripts/validate_release_live.py --live'
        $probeStartInfo.WorkingDirectory = $probeRoot
        $probeStartInfo.UseShellExecute = $false
        $probeStartInfo.CreateNoWindow = $true
        $probeStartInfo.EnvironmentVariables['NEBIUS_API_KEY'] = $probePlainKey
        $probeStartInfo.EnvironmentVariables['AUTOFRAME3D_SKIP_DOTENV'] = '1'
        $probeStartInfo.EnvironmentVariables['NEBIUS_MODEL'] = 'nvidia/Nemotron-3_5-Lightning'
        $probeProcess = New-Object System.Diagnostics.Process
        $probeProcess.StartInfo = $probeStartInfo
        if (-not $probeProcess.Start()) { throw 'Could not start release validation.' }
        $probeStartInfo.EnvironmentVariables.Remove('NEBIUS_API_KEY')
        $probePlainKey = $null
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($probeKeyPointer)
        $probeKeyPointer = [IntPtr]::Zero
        $probeSecureKey.Dispose()
        $probeSecureKey = $null
        $probeProcess.WaitForExit()
        Write-Host ('Validation exit code: {0}; inspect summary/report and review actual prose.' -f $probeProcess.ExitCode)
    }
    finally {
        if ($null -ne $probeStartInfo) { $probeStartInfo.EnvironmentVariables.Remove('NEBIUS_API_KEY') }
        if ($probeKeyPointer -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($probeKeyPointer) }
        if ($null -ne $probeSecureKey) { $probeSecureKey.Dispose() }
        $probePlainKey = $null
        if ($null -ne $probeProcess) {
            try {
                if (-not $probeProcess.HasExited) { $probeProcess.Kill(); $probeProcess.WaitForExit() }
            }
            finally { $probeProcess.Dispose() }
        }
    }
}
