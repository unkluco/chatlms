param(
    [Parameter(Mandatory=$true)][string]$PythonExe,
    [Parameter(Mandatory=$true)][string]$ScriptPath
)

$ErrorActionPreference = "Stop"

Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;

public static class BotJobNative
{
    public const uint CREATE_SUSPENDED = 0x00000004;
    public const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;
    public const int JobObjectExtendedLimitInformation = 9;
    public const uint INFINITE = 0xFFFFFFFF;

    [StructLayout(LayoutKind.Sequential)]
    public struct IO_COUNTERS
    {
        public ulong ReadOperationCount;
        public ulong WriteOperationCount;
        public ulong OtherOperationCount;
        public ulong ReadTransferCount;
        public ulong WriteTransferCount;
        public ulong OtherTransferCount;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_BASIC_LIMIT_INFORMATION
    {
        public long PerProcessUserTimeLimit;
        public long PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass;
        public uint SchedulingClass;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION
    {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)]
    public struct STARTUPINFO
    {
        public uint cb;
        public string lpReserved;
        public string lpDesktop;
        public string lpTitle;
        public uint dwX;
        public uint dwY;
        public uint dwXSize;
        public uint dwYSize;
        public uint dwXCountChars;
        public uint dwYCountChars;
        public uint dwFillAttribute;
        public uint dwFlags;
        public short wShowWindow;
        public short cbReserved2;
        public IntPtr lpReserved2;
        public IntPtr hStdInput;
        public IntPtr hStdOutput;
        public IntPtr hStdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    public struct PROCESS_INFORMATION
    {
        public IntPtr hProcess;
        public IntPtr hThread;
        public uint dwProcessId;
        public uint dwThreadId;
    }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool CreateProcess(
        string lpApplicationName,
        StringBuilder lpCommandLine,
        IntPtr lpProcessAttributes,
        IntPtr lpThreadAttributes,
        bool bInheritHandles,
        uint dwCreationFlags,
        IntPtr lpEnvironment,
        string lpCurrentDirectory,
        ref STARTUPINFO lpStartupInfo,
        out PROCESS_INFORMATION lpProcessInformation);

    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern IntPtr CreateJobObject(IntPtr lpJobAttributes, string lpName);

    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool SetInformationJobObject(
        IntPtr hJob,
        int infoType,
        IntPtr lpJobObjectInfo,
        uint cbJobObjectInfo);

    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool AssignProcessToJobObject(IntPtr hJob, IntPtr hProcess);

    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern uint ResumeThread(IntPtr hThread);
    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern uint WaitForSingleObject(IntPtr hHandle, uint dwMilliseconds);

    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool GetExitCodeProcess(IntPtr hProcess, out uint lpExitCode);

    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool CloseHandle(IntPtr hObject);

    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool TerminateProcess(IntPtr hProcess, uint uExitCode);

    [DllImport("kernel32.dll", SetLastError=true)]
    public static extern bool TerminateJobObject(IntPtr hJob, uint uExitCode);
}
"@

function Throw-Win32Error([string]$Message) {
    $code = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
    throw "$Message (Win32=$code)"
}

if (-not (Test-Path -LiteralPath $PythonExe)) {
    throw "Khong tim thay Python: $PythonExe"
}
if (-not (Test-Path -LiteralPath $ScriptPath)) {
    throw "Khong tim thay script bot: $ScriptPath"
}

# CreateProcess voi lpApplicationName on dinh hon khi dung duong dan tuyet doi.
$PythonExe = (Resolve-Path -LiteralPath $PythonExe).Path
$ScriptPath = (Resolve-Path -LiteralPath $ScriptPath).Path

$job = [BotJobNative]::CreateJobObject([IntPtr]::Zero, $null)
if ($job -eq [IntPtr]::Zero) {
    Throw-Win32Error "Khong tao duoc Job Object"
}
$info = New-Object BotJobNative+JOBOBJECT_EXTENDED_LIMIT_INFORMATION
$basic = $info.BasicLimitInformation
$basic.LimitFlags = [BotJobNative]::JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
$info.BasicLimitInformation = $basic
$size = [Runtime.InteropServices.Marshal]::SizeOf($info)
$ptr = [Runtime.InteropServices.Marshal]::AllocHGlobal($size)

try {
    [Runtime.InteropServices.Marshal]::StructureToPtr($info, $ptr, $false)
    if (-not [BotJobNative]::SetInformationJobObject(
        $job,
        [BotJobNative]::JobObjectExtendedLimitInformation,
        $ptr,
        [uint32]$size
    )) {
        Throw-Win32Error "Khong cau hinh duoc Job Object"
    }
}
finally {
    [Runtime.InteropServices.Marshal]::FreeHGlobal($ptr)
}

$si = New-Object BotJobNative+STARTUPINFO
$si.cb = [Runtime.InteropServices.Marshal]::SizeOf($si)
$pi = New-Object BotJobNative+PROCESS_INFORMATION

$workDir = Split-Path -Parent $ScriptPath
$healthPath = Join-Path $workDir "bot_health.json"
$configPath = Join-Path $workDir "config.json"
$watchdogStaleSeconds = 600
$watchdogCheckSeconds = 15
$watchdogStartupGraceSeconds = 120

try {
    if (Test-Path -LiteralPath $configPath) {
        $watchdogConfig = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
        if ($null -ne $watchdogConfig.watchdog_stale_seconds) {
            $watchdogStaleSeconds = [Math]::Max(120, [int]$watchdogConfig.watchdog_stale_seconds)
        }
        if ($null -ne $watchdogConfig.watchdog_check_seconds) {
            $watchdogCheckSeconds = [Math]::Max(5, [int]$watchdogConfig.watchdog_check_seconds)
        }
    }
}
catch {
    Write-Host "[WATCHDOG] Khong doc duoc config watchdog; dung gia tri mac dinh."
}

$cmd = '"' + $PythonExe + '" "' + $ScriptPath + '"'
$cmdLine = New-Object Text.StringBuilder
[void]$cmdLine.Append($cmd)

$parentProcess = $null
try {
    $selfInfo = Get-CimInstance Win32_Process -Filter "ProcessId=$PID"
    if ($selfInfo -and $selfInfo.ParentProcessId) {
        $parentProcess = Get-Process -Id ([int]$selfInfo.ParentProcessId) -ErrorAction Stop
    }
}
catch {
    $parentProcess = $null
}

$created = [BotJobNative]::CreateProcess(
    $PythonExe,
    $cmdLine,
    [IntPtr]::Zero,
    [IntPtr]::Zero,
    $true,
    [BotJobNative]::CREATE_SUSPENDED,
    [IntPtr]::Zero,
    $workDir,
    [ref]$si,
    [ref]$pi
)

if (-not $created) {
    [BotJobNative]::CloseHandle($job) | Out-Null
    Throw-Win32Error "Khong khoi dong duoc Python bot"
}

$finalExitCode = 0

try {
    if (-not [BotJobNative]::AssignProcessToJobObject($job, $pi.hProcess)) {
        [BotJobNative]::TerminateProcess($pi.hProcess, 1) | Out-Null
        Throw-Win32Error "Khong gan Python vao Job Object"
    }

    $resume = [BotJobNative]::ResumeThread($pi.hThread)
    if ($resume -eq 0xFFFFFFFF) {
        [BotJobNative]::TerminateProcess($pi.hProcess, 1) | Out-Null
        Throw-Win32Error "Khong resume duoc Python bot"
    }

    [BotJobNative]::CloseHandle($pi.hThread) | Out-Null
    $pi.hThread = [IntPtr]::Zero

    Write-Host "[JOB] Bot dang chay trong Windows Job Object."
    Write-Host "[JOB] Dong cua so nay se dung ca Python va browser cua bot."

    $parentGone = $false
    $watchdogTriggered = $false
    $processStartedAt = Get-Date
    $lastWatchdogCheck = Get-Date

    while ($true) {
        if ($parentProcess) {
            try {
                if ($parentProcess.HasExited) {
                    $parentGone = $true
                    Write-Host "[JOB] Phat hien cua so/launcher cha da dong."
                    break
                }
            }
            catch {
                $parentGone = $true
                Write-Host "[JOB] Khong con launcher cha. Dang dung bot..."
                break
            }
        }

        $now = Get-Date
        if (($now - $lastWatchdogCheck).TotalSeconds -ge $watchdogCheckSeconds) {
            $lastWatchdogCheck = $now
            $processAge = ($now - $processStartedAt).TotalSeconds
            $healthFresh = $false

            if (Test-Path -LiteralPath $healthPath) {
                try {
                    $health = Get-Content -LiteralPath $healthPath -Raw | ConvertFrom-Json
                    $updatedAt = [datetime]::Parse($health.updated_at)
                    $healthAge = ($now - $updatedAt).TotalSeconds
                    $belongsToCurrentRun = $updatedAt -ge $processStartedAt.AddSeconds(-5)
                    $healthFresh = $belongsToCurrentRun -and ($healthAge -lt $watchdogStaleSeconds)
                }
                catch {
                    $healthFresh = $false
                }
            }

            if (-not $healthFresh -and $processAge -ge $watchdogStartupGraceSeconds) {
                Write-Host "[WATCHDOG] Heartbeat mat/qua cu. Dang terminate Job Object de khoi dong lai..."
                [BotJobNative]::TerminateJobObject($job, 75) | Out-Null
                $watchdogTriggered = $true
                break
            }
        }

        $wait = [BotJobNative]::WaitForSingleObject($pi.hProcess, 500)
        if ($wait -eq 0) {
            break
        }
        if ($wait -ne 0x102) {
            Throw-Win32Error "Loi khi cho Python bot ket thuc"
        }
    }

    if ($watchdogTriggered) {
        $finalExitCode = 75
    }
    elseif (-not $parentGone) {
        [uint32]$exitCode = 0
        if (-not [BotJobNative]::GetExitCodeProcess($pi.hProcess, [ref]$exitCode)) {
            Throw-Win32Error "Khong doc duoc exit code cua bot"
        }
        $finalExitCode = [int]$exitCode
    }
}
finally {
    if ($pi.hThread -ne [IntPtr]::Zero) {
        [BotJobNative]::CloseHandle($pi.hThread) | Out-Null
    }
    if ($pi.hProcess -ne [IntPtr]::Zero) {
        [BotJobNative]::CloseHandle($pi.hProcess) | Out-Null
    }
    if ($job -ne [IntPtr]::Zero) {
        [BotJobNative]::CloseHandle($job) | Out-Null
    }
}

exit $finalExitCode
