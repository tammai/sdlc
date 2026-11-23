# Runs hosts/hook.py for Cursor on Windows, where Cursor runs a hook command as a Windows PowerShell 5.1 script.
# There python3 may be missing, or be the Microsoft Store stub that prints where to get Python and exits 9009.
# Every python3, python and py on PATH is tried in that order, each with a quick check that it is Python 3.9 or
# newer, with an empty stdin so only the one chosen reads Cursor's event. Cursor hands the event in as pipeline
# input (cursor-agent 2026.11.22), which goes on to Python as UTF-8; with none, Python reads this script's stdin.
# Hand-written; hosts.py builds the command that calls it (cursor_hooks).
$payload = @($input | Where-Object { $null -ne $_ })
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$env:PYTHONUTF8 = '1'
$hook = Join-Path (Split-Path -Parent $PSScriptRoot) 'hook.py'
foreach ($name in @('python3', 'python', 'py')) {
    $extra = @()
    if ($name -eq 'py') { $extra = @('-3') }
    foreach ($cmd in @(Get-Command $name -CommandType Application -ErrorAction SilentlyContinue)) {
        $null | & $cmd.Source @extra -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0) {
            if ($payload.Count) { $payload | & $cmd.Source @extra $hook @args } else { & $cmd.Source @extra $hook @args }
            exit $LASTEXITCODE
        }
    }
}
# Exit 1 with nothing on stdout: Cursor then goes on as if there were no hook (never a deny)
[Console]::Error.WriteLine('sdlc hooks: no working Python 3.9+ found (tried python3, python, py -3); install Python from https://python.org')
exit 1
