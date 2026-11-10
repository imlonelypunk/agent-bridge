param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^[0-9a-fA-F-]{36}$')]
    [string] $ThreadId,
    [string] $Workspace = (Split-Path -Parent $PSScriptRoot),
    [string] $ChannelDirectory = (Join-Path $env:USERPROFILE '.agent-bridge\channel'),
    [ValidateRange(0, 9223372036854775807)]
    [long] $After = 0,
    [string] $TaskName = 'AgentBridge-Codex-Listener'
)

$ErrorActionPreference = 'Stop'
$python = (Get-Command python.exe -ErrorAction Stop).Source
$pythonw = Join-Path (Split-Path -Parent $python) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonw -PathType Leaf)) { throw 'pythonw.exe is required for a hidden listener.' }
$bridge = (Resolve-Path -LiteralPath (Join-Path (Split-Path -Parent $PSScriptRoot) 'listener_service.py')).Path
$Workspace = (Resolve-Path -LiteralPath $Workspace).Path
if ($TaskName -notmatch '^[a-zA-Z0-9_-]{1,80}$') { throw 'Invalid task name.' }
foreach ($value in @($python, $bridge, $Workspace, $ChannelDirectory)) {
    if ($value.Contains('"')) { throw 'Paths containing quotation marks are unsupported.' }
}
$arguments = '"{0}" --agent codex --workspace "{1}" --channel-dir "{2}" postman --thread {3} --after {4} --timeout-seconds 86400' -f $bridge, $Workspace, $ChannelDirectory.TrimEnd('\'), $ThreadId, $After
$action = New-ScheduledTaskAction -Execute $pythonw -Argument $arguments -WorkingDirectory $Workspace
$logon = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$daily = New-ScheduledTaskTrigger -Daily -At '00:00'
$repeat = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 1)
$daily.Repetition = $repeat.Repetition
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 25) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger @($logon, $daily) -Settings $settings -Description 'Agent Bridge listener for a selected Codex chat' -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Output "Registered and started $TaskName for Codex chat $ThreadId."
