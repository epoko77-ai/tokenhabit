# vhs demo.tape — headless recording of the tokenhabit README demo.
# Run from this directory:  PATH=/tmp/thverify/bin:$PATH vhs demo.tape
# Output goes to ../../assets/demo.gif

Output ../../assets/demo.gif

Set Shell "zsh"
Set FontSize 16
Set Width 1200
Set Height 880
Set Padding 22
Set Theme "Catppuccin Mocha"
Set TypingSpeed 60ms

Hide
Type "clear"
Enter
Show

Sleep 600ms
Type "tokenhabit --project demo-logs"
Sleep 900ms
Enter
Sleep 7s
