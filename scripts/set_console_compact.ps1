param(
    [int]$FontSize = 12,
    [int]$Columns = 110,
    [int]$Rows = 36
)

$ErrorActionPreference = "SilentlyContinue"

try {
    $source = @"
using System;
using System.Runtime.InteropServices;

[StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
public struct CONSOLE_FONT_INFO_EX {
    public uint cbSize;
    public uint nFont;
    public short dwFontSizeX;
    public short dwFontSizeY;
    public int FontFamily;
    public int FontWeight;
    [MarshalAs(UnmanagedType.ByValTStr, SizeConst = 32)]
    public string FaceName;
}

public static class ConsoleFont {
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern IntPtr GetStdHandle(int nStdHandle);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool GetCurrentConsoleFontEx(IntPtr hConsoleOutput, bool bMaximumWindow, ref CONSOLE_FONT_INFO_EX lpConsoleCurrentFontEx);

    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool SetCurrentConsoleFontEx(IntPtr hConsoleOutput, bool bMaximumWindow, ref CONSOLE_FONT_INFO_EX lpConsoleCurrentFontEx);
}
"@
    Add-Type -TypeDefinition $source -ErrorAction SilentlyContinue | Out-Null
    $handle = [ConsoleFont]::GetStdHandle(-11)
    $font = New-Object CONSOLE_FONT_INFO_EX
    $font.cbSize = [Runtime.InteropServices.Marshal]::SizeOf($font)
    if ([ConsoleFont]::GetCurrentConsoleFontEx($handle, $false, [ref]$font)) {
        $font.dwFontSizeY = [int16]$FontSize
        $font.dwFontSizeX = 0
        $font.FaceName = "Consolas"
        [ConsoleFont]::SetCurrentConsoleFontEx($handle, $false, [ref]$font) | Out-Null
    }
} catch {
    # Windows Terminal may ignore runtime font changes. Compact banners still fit.
}

try {
    $raw = $Host.UI.RawUI
    $buffer = $raw.BufferSize
    $window = $raw.WindowSize
    $buffer.Width = [Math]::Max($buffer.Width, $Columns)
    $buffer.Height = [Math]::Max($buffer.Height, 900)
    $raw.BufferSize = $buffer
    $window.Width = [Math]::Min($Columns, $raw.MaxPhysicalWindowSize.Width)
    $window.Height = [Math]::Min($Rows, $raw.MaxPhysicalWindowSize.Height)
    $raw.WindowSize = $window
} catch {
}
