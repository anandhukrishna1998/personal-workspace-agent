import psutil
import platform
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("system-monitor")

def format_bytes(bytes_value: int) -> str:
    """Convert bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} PB"

def format_uptime(seconds: float) -> str:
    """Format uptime in human readable format."""
    uptime = timedelta(seconds=seconds)
    days = uptime.days
    hours, remainder = divmod(uptime.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m {seconds}s"

@mcp.tool()
async def get_system_info() -> str:
    """Get comprehensive system information.
    
    Returns:
        Detailed system information including OS, CPU, memory, and disk usage
    """
    try:
        # Basic system info
        system_info = {
            'OS': f"{platform.system()} {platform.release()}",
            'Architecture': platform.machine(),
            'Processor': platform.processor(),
            'Hostname': platform.node(),
            'Python Version': platform.python_version(),
        }
        
        # CPU information
        cpu_count = psutil.cpu_count(logical=False)
        cpu_count_logical = psutil.cpu_count(logical=True)
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory information
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        # Disk information
        disk = psutil.disk_usage('/')
        
        # Boot time
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        
        result = "🖥️ System Information\n"
        result += "=" * 50 + "\n\n"
        
        # System details
        result += "📋 System Details:\n"
        for key, value in system_info.items():
            result += f"  {key}: {value}\n"
        result += f"  Boot Time: {boot_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        result += f"  Uptime: {format_uptime(uptime.total_seconds())}\n\n"
        
        # CPU information
        result += "🔧 CPU Information:\n"
        result += f"  Physical Cores: {cpu_count}\n"
        result += f"  Logical Cores: {cpu_count_logical}\n"
        result += f"  CPU Usage: {cpu_percent}%\n"
        
        # Per-core CPU usage
        cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
        result += f"  Per-Core Usage: {', '.join([f'{core:.1f}%' for core in cpu_per_core])}\n\n"
        
        # Memory information
        result += "💾 Memory Information:\n"
        result += f"  Total RAM: {format_bytes(memory.total)}\n"
        result += f"  Available RAM: {format_bytes(memory.available)}\n"
        result += f"  Used RAM: {format_bytes(memory.used)}\n"
        result += f"  RAM Usage: {memory.percent}%\n"
        result += f"  Swap Total: {format_bytes(swap.total)}\n"
        result += f"  Swap Used: {format_bytes(swap.used)}\n"
        result += f"  Swap Usage: {swap.percent}%\n\n"
        
        # Disk information
        result += "💿 Disk Information:\n"
        result += f"  Total Disk: {format_bytes(disk.total)}\n"
        result += f"  Used Disk: {format_bytes(disk.used)}\n"
        result += f"  Free Disk: {format_bytes(disk.free)}\n"
        result += f"  Disk Usage: {disk.percent}%\n"
        
        return result
        
    except Exception as e:
        return f"Error getting system information: {str(e)}"

@mcp.tool()
async def get_processes(limit: int = 10, sort_by: str = "cpu") -> str:
    """Get information about running processes.
    
    Args:
        limit: Number of processes to return (default: 10)
        sort_by: Sort by 'cpu', 'memory', or 'pid' (default: cpu)
    
    Returns:
        List of running processes with their resource usage
    """
    try:
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info', 'status']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort processes
        if sort_by == "cpu":
            processes.sort(key=lambda x: x['cpu_percent'] or 0, reverse=True)
        elif sort_by == "memory":
            processes.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
        elif sort_by == "pid":
            processes.sort(key=lambda x: x['pid'])
        
        result = f"🔄 Top {limit} Processes (sorted by {sort_by}):\n"
        result += "=" * 80 + "\n"
        result += f"{'PID':<8} {'Name':<25} {'CPU%':<8} {'Memory%':<10} {'Memory':<12} {'Status':<10}\n"
        result += "-" * 80 + "\n"
        
        for proc in processes[:limit]:
            pid = proc['pid']
            name = proc['name'][:24] if proc['name'] else 'N/A'
            cpu_percent = f"{proc['cpu_percent']:.1f}%" if proc['cpu_percent'] else "0.0%"
            memory_percent = f"{proc['memory_percent']:.1f}%" if proc['memory_percent'] else "0.0%"
            memory_info = format_bytes(proc['memory_info'].rss) if proc['memory_info'] else "N/A"
            status = proc['status']
            
            result += f"{pid:<8} {name:<25} {cpu_percent:<8} {memory_percent:<10} {memory_info:<12} {status:<10}\n"
        
        return result
        
    except Exception as e:
        return f"Error getting process information: {str(e)}"

@mcp.tool()
async def get_disk_usage() -> str:
    """Get detailed disk usage information for all mounted drives.
    
    Returns:
        Disk usage information for all mounted drives
    """
    try:
        result = "💿 Disk Usage Information\n"
        result += "=" * 60 + "\n\n"
        
        # Get all disk partitions
        partitions = psutil.disk_partitions()
        
        for partition in partitions:
            try:
                partition_usage = psutil.disk_usage(partition.mountpoint)
                
                result += f"📁 Drive: {partition.device}\n"
                result += f"  Mount Point: {partition.mountpoint}\n"
                result += f"  File System: {partition.fstype}\n"
                result += f"  Total Size: {format_bytes(partition_usage.total)}\n"
                result += f"  Used: {format_bytes(partition_usage.used)}\n"
                result += f"  Free: {format_bytes(partition_usage.free)}\n"
                result += f"  Usage: {partition_usage.percent}%\n"
                
                # Add usage bar
                bar_length = 20
                filled_length = int(bar_length * partition_usage.percent / 100)
                bar = "█" * filled_length + "░" * (bar_length - filled_length)
                result += f"  Progress: [{bar}] {partition_usage.percent}%\n\n"
                
            except PermissionError:
                result += f"📁 Drive: {partition.device}\n"
                result += f"  Mount Point: {partition.mountpoint}\n"
                result += f"  File System: {partition.fstype}\n"
                result += f"  Status: Access Denied\n\n"
        
        return result
        
    except Exception as e:
        return f"Error getting disk usage: {str(e)}"

@mcp.tool()
async def get_network_info() -> str:
    """Get network interface and connection information.
    
    Returns:
        Network interface statistics and active connections
    """
    try:
        result = "🌐 Network Information\n"
        result += "=" * 50 + "\n\n"
        
        # Network interfaces
        result += "📡 Network Interfaces:\n"
        interfaces = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        
        for interface_name, interface_addresses in interfaces.items():
            if interface_name in stats:
                stat = stats[interface_name]
                result += f"  {interface_name}:\n"
                result += f"    Status: {'Up' if stat.isup else 'Down'}\n"
                result += f"    Speed: {stat.speed} Mbps\n"
                result += f"    MTU: {stat.mtu}\n"
                
                for address in interface_addresses:
                    result += f"    {address.family.name}: {address.address}\n"
                result += "\n"
        
        # Network I/O statistics
        net_io = psutil.net_io_counters()
        result += "📊 Network I/O Statistics:\n"
        result += f"  Bytes Sent: {format_bytes(net_io.bytes_sent)}\n"
        result += f"  Bytes Received: {format_bytes(net_io.bytes_recv)}\n"
        result += f"  Packets Sent: {net_io.packets_sent:,}\n"
        result += f"  Packets Received: {net_io.packets_recv:,}\n"
        result += f"  Errors In: {net_io.errin:,}\n"
        result += f"  Errors Out: {net_io.errout:,}\n"
        result += f"  Drops In: {net_io.dropin:,}\n"
        result += f"  Drops Out: {net_io.dropout:,}\n\n"
        
        # Active connections
        result += "🔗 Active Connections:\n"
        connections = psutil.net_connections(kind='inet')
        
        if connections:
            result += f"{'Local Address':<20} {'Remote Address':<20} {'Status':<12} {'PID':<8}\n"
            result += "-" * 70 + "\n"
            
            for conn in connections[:20]:  # Limit to first 20 connections
                local_addr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
                remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
                status = conn.status
                pid = conn.pid if conn.pid else "N/A"
                
                result += f"{local_addr:<20} {remote_addr:<20} {status:<12} {pid:<8}\n"
        else:
            result += "  No active connections found.\n"
        
        return result
        
    except Exception as e:
        return f"Error getting network information: {str(e)}"

@mcp.tool()
async def get_system_health() -> str:
    """Get overall system health status and alerts.
    
    Returns:
        System health summary with warnings and recommendations
    """
    try:
        result = "🏥 System Health Check\n"
        result += "=" * 40 + "\n\n"
        
        alerts = []
        warnings = []
        
        # CPU check
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:
            alerts.append(f"⚠️ High CPU usage: {cpu_percent:.1f}%")
        elif cpu_percent > 60:
            warnings.append(f"⚡ Moderate CPU usage: {cpu_percent:.1f}%")
        else:
            result += f"✅ CPU usage: {cpu_percent:.1f}% (Normal)\n"
        
        # Memory check
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            alerts.append(f"🚨 Critical memory usage: {memory.percent:.1f}%")
        elif memory.percent > 80:
            alerts.append(f"⚠️ High memory usage: {memory.percent:.1f}%")
        elif memory.percent > 70:
            warnings.append(f"⚡ Moderate memory usage: {memory.percent:.1f}%")
        else:
            result += f"✅ Memory usage: {memory.percent:.1f}% (Normal)\n"
        
        # Disk check
        disk = psutil.disk_usage('/')
        if disk.percent > 95:
            alerts.append(f"🚨 Critical disk usage: {disk.percent:.1f}%")
        elif disk.percent > 90:
            alerts.append(f"⚠️ High disk usage: {disk.percent:.1f}%")
        elif disk.percent > 80:
            warnings.append(f"⚡ Moderate disk usage: {disk.percent:.1f}%")
        else:
            result += f"✅ Disk usage: {disk.percent:.1f}% (Normal)\n"
        
        # Temperature check (if available)
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current and entry.current > 80:
                            alerts.append(f"🌡️ High temperature on {name}: {entry.current}°C")
                        elif entry.current and entry.current > 70:
                            warnings.append(f"🌡️ Elevated temperature on {name}: {entry.current}°C")
        except AttributeError:
            pass  # Temperature monitoring not available on this system
        
        # Display alerts and warnings
        if alerts:
            result += "\n🚨 ALERTS:\n"
            for alert in alerts:
                result += f"  {alert}\n"
        
        if warnings:
            result += "\n⚡ WARNINGS:\n"
            for warning in warnings:
                result += f"  {warning}\n"
        
        if not alerts and not warnings:
            result += "\n🎉 System is running optimally!\n"
        
        # Recommendations
        result += "\n💡 Recommendations:\n"
        if cpu_percent > 60:
            result += "  - Consider closing unnecessary applications\n"
        if memory.percent > 70:
            result += "  - Close unused programs to free up memory\n"
        if disk.percent > 80:
            result += "  - Clean up disk space by removing unnecessary files\n"
        
        return result
        
    except Exception as e:
        return f"Error checking system health: {str(e)}"

@mcp.resource("system://{resource}")
def system_resource(resource: str) -> str:
    """Access system resources"""
    return f"System resource: {resource}"

if __name__ == "__main__":
    # Run the server
    import asyncio
    asyncio.run(mcp.run())
