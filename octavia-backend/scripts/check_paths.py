from pathlib import Path
paths=[
    r"C:/Users/robbd/Documents/Git/octavia/octavia-backend/uploads/users/f271b1f1-2761-48e4-9c0e-7208242442b2/audio/380bfd21-39c4-4ed7-a928-973a8d2023ad_test_audio_transcript_translated.json",
    r"C:\\Users\\robbd\\Documents\\Git\\octavia\\octavia-backend\\uploads\\users\\f271b1f1-2761-48e4-9c0e-7208242442b2\\audio\\380bfd21-39c4-4ed7-a928-973a8d2023ad_test_audio_transcript_translated.json"
]
for p in paths:
    path=Path(p)
    print(p)
    print('exists:', path.exists())
    if path.exists():
        print('size:', path.stat().st_size)
    print('as_posix:', path.as_posix())
    print('as_uri:', path.as_uri())
    print('---')
