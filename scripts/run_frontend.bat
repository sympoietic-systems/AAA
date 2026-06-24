@echo off
cd /d "%~dp0..\frontend"

rem Disable Windows Console QuickEdit mode to prevent suspension when clicking in terminal
powershell -NoProfile -Command "$sig = '[DllImport(\"kernel32.dll\")] public static extern IntPtr GetStdHandle(int n); [DllImport(\"kernel32.dll\")] public static extern bool GetConsoleMode(IntPtr h, out uint m); [DllImport(\"kernel32.dll\")] public static extern bool SetConsoleMode(IntPtr h, uint m);'; $type = Add-Type -MemberDefinition $sig -Name 'ConsoleHelper' -Namespace 'Win32' -PassThru; $h = $type::GetStdHandle(-10); $m = 0; if ($type::GetConsoleMode($h, [ref]$m)) { $type::SetConsoleMode($h, ($m -band -bnot 0x0040 -band -bnot 0x0020) -bor 0x0080) }"

npm run dev