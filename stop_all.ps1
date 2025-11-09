# AI-Trader 停止脚本 (Windows PowerShell)
# 停止所有运行中的服务

# 设置错误处理
$ErrorActionPreference = "Continue"

# 项目根目录
$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$PID_DIR = Join-Path $PROJECT_ROOT "pids"
$MAIN_PID_FILE = Join-Path $PID_DIR "main.pid"
$MCP_PID_FILE = Join-Path $PID_DIR "mcp.pid"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🛑 AI-Trader 停止脚本 (Windows)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 停止main.py
if (Test-Path $MAIN_PID_FILE) {
    $pid = Get-Content $MAIN_PID_FILE -ErrorAction SilentlyContinue
    if ($pid) {
        try {
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "🛑 正在停止 main.py (PID: $pid)..." -ForegroundColor Yellow
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Remove-Item $MAIN_PID_FILE -Force -ErrorAction SilentlyContinue
                Write-Host "✅ main.py 已停止" -ForegroundColor Green
            } else {
                Write-Host "⚠️  main.py 进程不存在 (PID: $pid)" -ForegroundColor Yellow
                Remove-Item $MAIN_PID_FILE -Force -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Host "⚠️  停止进程时出错: $_" -ForegroundColor Yellow
            Remove-Item $MAIN_PID_FILE -Force -ErrorAction SilentlyContinue
        }
    }
} else {
    Write-Host "⚠️  main.py PID文件不存在，尝试查找进程..." -ForegroundColor Yellow
    # 尝试通过进程命令行查找并kill
    try {
        $processes = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | Where-Object {
            $_.CommandLine -like "*main.py*"
        }
        if ($processes) {
            foreach ($proc in $processes) {
                Write-Host "🛑 正在停止 main.py (PID: $($proc.ProcessId))..." -ForegroundColor Yellow
                Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
                Write-Host "✅ 已通过进程名停止 main.py (PID: $($proc.ProcessId))" -ForegroundColor Green
            }
        } else {
            Write-Host "ℹ️  未找到运行中的 main.py 进程" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "ℹ️  无法查找进程: $_" -ForegroundColor Yellow
    }
}

# 停止MCP服务
if (Test-Path $MCP_PID_FILE) {
    $pid = Get-Content $MCP_PID_FILE -ErrorAction SilentlyContinue
    if ($pid) {
        try {
            $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "🛑 正在停止 MCP服务 (PID: $pid)..." -ForegroundColor Yellow
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
                Remove-Item $MCP_PID_FILE -Force -ErrorAction SilentlyContinue
                Write-Host "✅ MCP服务已停止" -ForegroundColor Green
            } else {
                Write-Host "⚠️  MCP服务进程不存在 (PID: $pid)" -ForegroundColor Yellow
                Remove-Item $MCP_PID_FILE -Force -ErrorAction SilentlyContinue
            }
        } catch {
            Write-Host "⚠️  停止进程时出错: $_" -ForegroundColor Yellow
            Remove-Item $MCP_PID_FILE -Force -ErrorAction SilentlyContinue
        }
    }
} else {
    Write-Host "⚠️  MCP服务 PID文件不存在，尝试查找进程..." -ForegroundColor Yellow
    # 尝试通过进程命令行查找并kill
    try {
        $processes = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | Where-Object {
            $_.CommandLine -like "*start_mcp_services.py*"
        }
        if ($processes) {
            foreach ($proc in $processes) {
                Write-Host "🛑 正在停止 MCP服务 (PID: $($proc.ProcessId))..." -ForegroundColor Yellow
                Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
                Write-Host "✅ 已通过进程名停止 MCP服务 (PID: $($proc.ProcessId))" -ForegroundColor Green
            }
        } else {
            Write-Host "ℹ️  未找到运行中的 MCP服务进程" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "ℹ️  无法查找进程: $_" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "✅ 停止完成！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan

# 显示仍在运行的Python进程（可选）
Write-Host ""
Write-Host "📊 检查是否还有相关进程运行:" -ForegroundColor Cyan
try {
    $remaining = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*main.py*" -or $_.CommandLine -like "*start_mcp_services.py*"
    }
    
    if ($remaining) {
        Write-Host "⚠️  发现以下进程:" -ForegroundColor Yellow
        $remaining | ForEach-Object {
            Write-Host "  PID: $($_.ProcessId) - $($_.Name)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "✅ 没有发现相关进程" -ForegroundColor Green
    }
} catch {
    Write-Host "ℹ️  无法检查进程状态" -ForegroundColor Yellow
}

