from pathlib import Path
text = Path('jarvis_voice_commands.py').read_text('utf-8')
lines = text.splitlines()
for i in range(370, 410):
    print(f'{i+1:03d}: {repr(lines[i])}')
print('--- full segment ---')
print(repr(text[text.index('        # Démo voix'):text.index('if __name__ == "__main__"')]))
