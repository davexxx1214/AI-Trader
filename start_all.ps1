# AI-Trader 一键启动脚本 (Windows PowerShell)
# 后台启动服务并实时显示日志

# 设置错误处理
$ErrorActionPreference = "Stop"

# 项目根目录
$PROJECT_ROOT = Split-Path -Parent $MyInvocation.MyCommand.Path
$MCP_DIR = Join-Path $PROJECT_ROOT "agent_tools"
$MAIN_SCRIPT = Join-Path $PROJECT_ROOT "main.py"
$LOG_DIR = Join-Path $PROJECT_ROOT "logs"
$PID_DIR = Join-Path $PROJECT_ROOT "pids"

# 创建必要的目录
if (-not (Test-Path $LOG_DIR)) { New-Item -ItemType Directory -Path $LOG_DIR | Out-Null }
if (-not (Test-Path $PID_DIR)) { New-Item -ItemType Directory -Path $PID_DIR | Out-Null }

# MCP服务端口配置
$MATH_PORT = if ($env:MATH_HTTP_PORT) { [int]$env:MATH_HTTP_PORT } else { 8000 }
$SEARCH_PORT = if ($env:SEARCH_HTTP_PORT) { [int]$env:SEARCH_HTTP_PORT } else { 8001 }
$TRADE_PORT = if ($env:TRADE_HTTP_PORT) { [int]$env:TRADE_HTTP_PORT } else { 8002 }
$PRICE_PORT = if ($env:GETPRICE_HTTP_PORT) { [int]$env:GETPRICE_HTTP_PORT } else { 8003 }

# 日志文件
$MCP_LOG = Join-Path $LOG_DIR "mcp_services.log"
$MAIN_LOG = Join-Path $LOG_DIR "main_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$MAIN_PID_FILE = Join-Path $PID_DIR "main.pid"
$MCP_PID_FILE = Join-Path $PID_DIR "mcp.pid"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🚀 AI-Trader 一键启动脚本 (Windows)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 检查端口是否被占用
function Test-Port {
    param([int]$Port)
    try {
        $connection = Test-NetConnection -ComputerName localhost -Port $Port -WarningAction SilentlyContinue -InformationLevel Quiet
        return $connection
    } catch {
        return $false
    }
}

# 检查进程是否在运行
function Test-ProcessRunning {
    param([string]$PidFile)
    if (Test-Path $PidFile) {
        $pid = Get-Content $PidFile -ErrorAction SilentlyContinue
        if ($pid) {
            try {
                $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
                if ($process) {
                    return $true
                } else {
                    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
                    return $false
                }
            } catch {
                Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
                return $false
            }
        }
    }
    return $false
}

# 检查MCP服务状态
function Test-MCPServices {
    Write-Host ""
    Write-Host "📊 检查MCP服务状态..." -ForegroundColor Cyan
    
    $runningCount = 0
    $totalCount = 4
    
    if (Test-Port -Port $MATH_PORT) {
        Write-Host "✅ Math服务正在运行 (端口: $MATH_PORT)" -ForegroundColor Green
        $runningCount++
    } else {
        Write-Host "❌ Math服务未运行 (端口: $MATH_PORT)" -ForegroundColor Red
    }
    
    if (Test-Port -Port $SEARCH_PORT) {
        Write-Host "✅ Search服务正在运行 (端口: $SEARCH_PORT)" -ForegroundColor Green
        $runningCount++
    } else {
        Write-Host "❌ Search服务未运行 (端口: $SEARCH_PORT)" -ForegroundColor Red
    }
    
    if (Test-Port -Port $TRADE_PORT) {
        Write-Host "✅ Trade服务正在运行 (端口: $TRADE_PORT)" -ForegroundColor Green
        $runningCount++
    } else {
        Write-Host "❌ Trade服务未运行 (端口: $TRADE_PORT)" -ForegroundColor Red
    }
    
    if (Test-Port -Port $PRICE_PORT) {
        Write-Host "✅ Price服务正在运行 (端口: $PRICE_PORT)" -ForegroundColor Green
        $runningCount++
    } else {
        Write-Host "❌ Price服务未运行 (端口: $PRICE_PORT)" -ForegroundColor Red
    }
    
    return ($runningCount -eq $totalCount)
}

# 启动MCP服务
function Start-MCPServices {
    Write-Host ""
    Write-Host "🚀 正在启动MCP服务..." -ForegroundColor Yellow
    
    # 检查是否已经在运行
    if (Test-ProcessRunning -PidFile $MCP_PID_FILE) {
        $pid = Get-Content $MCP_PID_FILE
        Write-Host "✅ MCP服务已在运行 (PID: $pid)" -ForegroundColor Green
        return $true
    }
    
    Push-Location $MCP_DIR
    
    try {
        # 启动进程（后台运行，独立于Terminal）
        $process = Start-Process -FilePath "python" `
            -ArgumentList "start_mcp_services.py" `
            -WorkingDirectory $MCP_DIR `
            -WindowStyle Hidden `
            -PassThru `
            -RedirectStandardOutput $MCP_LOG `
            -RedirectStandardError $MCP_LOG
        
        # 保存PID
        $process.Id | Out-File -FilePath $MCP_PID_FILE -Encoding utf8
        
        Write-Host "✅ MCP服务已启动 (PID: $($process.Id))" -ForegroundColor Green
        Write-Host "📝 日志文件: $MCP_LOG" -ForegroundColor Cyan
        
        # 等待服务启动
        Write-Host "⏳ 等待MCP服务启动..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        # 检查服务状态
        if (Test-MCPServices) {
            Write-Host "✅ MCP服务启动成功！" -ForegroundColor Green
            return $true
        } else {
            Write-Host "⚠️  MCP服务可能未完全启动，请检查日志" -ForegroundColor Yellow
            return $false
        }
    } catch {
        Write-Host "❌ 启动MCP服务失败: $_" -ForegroundColor Red
        return $false
    } finally {
        Pop-Location
    }
}

# 检查main.py状态
function Test-Main {
    Write-Host ""
    Write-Host "📊 检查main.py状态..." -ForegroundColor Cyan
    
    if (Test-ProcessRunning -PidFile $MAIN_PID_FILE) {
        $pid = Get-Content $MAIN_PID_FILE
        Write-Host "✅ main.py 正在运行 (PID: $pid)" -ForegroundColor Green
        return $true
    } else {
        Write-Host "❌ main.py 未运行" -ForegroundColor Red
        return $false
    }
}

# 启动main.py
function Start-Main {
    param([string[]]$Arguments = @())
    
    Write-Host ""
    Write-Host "🚀 正在启动main.py..." -ForegroundColor Yellow
    
    # 检查是否已经在运行
    if (Test-ProcessRunning -PidFile $MAIN_PID_FILE) {
        $pid = Get-Content $MAIN_PID_FILE
        Write-Host "✅ main.py 已在运行 (PID: $pid)" -ForegroundColor Green
        return $true
    }
    
    Push-Location $PROJECT_ROOT
    
    try {
        # 构建参数
        $argsList = @("`"$MAIN_SCRIPT`"")
        if ($Arguments.Count -gt 0) {
            $argsList += $Arguments
        }
        
        # 启动进程（后台运行，独立于Terminal）
        $process = Start-Process -FilePath "python" `
            -ArgumentList $argsList `
            -WorkingDirectory $PROJECT_ROOT `
            -WindowStyle Hidden `
            -PassThru `
            -RedirectStandardOutput $MAIN_LOG `
            -RedirectStandardError $MAIN_LOG
        
        # 保存PID
        $process.Id | Out-File -FilePath $MAIN_PID_FILE -Encoding utf8
        
        Write-Host "✅ main.py 已启动 (PID: $($process.Id))" -ForegroundColor Green
        Write-Host "📝 日志文件: $MAIN_LOG" -ForegroundColor Cyan
        
        # 等待一下让日志生成
        Start-Sleep -Seconds 2
        
        # 显示日志的最后30行
        if (Test-Path $MAIN_LOG) {
            Write-Host ""
            Write-Host "📋 显示日志文件最后30行:" -ForegroundColor Cyan
            Write-Host "============================================================" -ForegroundColor Cyan
            Get-Content $MAIN_LOG -Tail 30 -ErrorAction SilentlyContinue
            Write-Host "============================================================" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "💡 提示: 使用以下命令查看实时日志:" -ForegroundColor Green
            Write-Host "   Get-Content $MAIN_LOG -Wait -Tail 50" -ForegroundColor Yellow
        }
        
        return $true
    } catch {
        Write-Host "❌ 启动main.py失败: $_" -ForegroundColor Red
        return $false
    } finally {
        Pop-Location
    }
}

# 主函数
function Main {
    param([string[]]$Arguments = @())
    
    # 检查MCP服务
    if (-not (Test-MCPServices)) {
        Start-MCPServices | Out-Null
    } else {
        Write-Host "✅ MCP服务已在运行" -ForegroundColor Green
    }
    
    # 等待一下确保MCP服务完全启动
    Start-Sleep -Seconds 2
    
    # 检查main.py
    if (-not (Test-Main)) {
        Start-Main -Arguments $Arguments | Out-Null
    } else {
        Write-Host "✅ main.py 已在运行" -ForegroundColor Green
        # 显示最新的日志
        $latestLog = Get-ChildItem -Path $LOG_DIR -Filter "main_*.log" -ErrorAction SilentlyContinue | 
                     Sort-Object LastWriteTime -Descending | 
                     Select-Object -First 1
        
        if ($latestLog) {
            Write-Host ""
            Write-Host "📋 显示最新日志文件最后30行:" -ForegroundColor Cyan
            Write-Host "============================================================" -ForegroundColor Cyan
            Get-Content $latestLog.FullName -Tail 30 -ErrorAction SilentlyContinue
            Write-Host "============================================================" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "💡 提示: 使用以下命令查看实时日志:" -ForegroundColor Green
            Write-Host "   Get-Content $($latestLog.FullName) -Wait -Tail 50" -ForegroundColor Yellow
        }
    }
    
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "✅ 启动完成！" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "📁 日志目录: $LOG_DIR" -ForegroundColor Cyan
    Write-Host "📁 PID文件目录: $PID_DIR" -ForegroundColor Cyan
    Write-Host "💡 提示: 所有服务已在后台运行" -ForegroundColor Green
    Write-Host "💡 提示: 关闭Terminal后进程会继续运行" -ForegroundColor Green
    Write-Host ""
}

# 运行主函数
Main -Arguments $args

