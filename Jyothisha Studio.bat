@echo off
rem Jyothisha Studio: the website on this computer only, for making the paid reports with your notes.
rem Double-click to start; your browser opens on it. Close the black window to stop it.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\studio.ps1"
