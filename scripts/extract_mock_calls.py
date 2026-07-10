"""
Script to extract mock call .wav files from data_shard_000_zstd.parquet.

Why this approach:
We extract real Indic-audio dialogue sample .wav files to serve as realistic test files 
for transcription, diarisation, and analysis, as defined in PLAN.md §2a.
"""

import os
import pandas as pd

def main():
    """
    Extracts the first 5 audio entries from the local zstd parquet shard and
    writes them as individual WAV files under data/mock_calls/.
    """
    parquet_path = "data_shard_000_zstd.parquet"
    output_dir = "data/mock_calls"
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(parquet_path):
        print(f"Error: {parquet_path} not found in the workspace root.")
        return
        
    print("Reading parquet file...")
    # Read only the id and audio columns to save memory
    df = pd.read_parquet(parquet_path, columns=['id', 'audio'])
    print(f"Parquet file read successfully. Total rows: {len(df)}")
    
    # Extract the first 5 rows
    count = 0
    for i in range(len(df)):
        if count >= 100:
            break
            
        row = df.iloc[i]
        audio_data = row['audio']
        
        # Check if 'bytes' contains the raw WAV content
        if isinstance(audio_data, dict) and 'bytes' in audio_data:
            wav_bytes = audio_data['bytes']
            call_id = row['id']
            filename = f"call_{call_id}.wav"
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(wav_bytes)
            print(f"Extracted {filepath} ({len(wav_bytes)} bytes)")
            count += 1
        else:
            print(f"Row {i} (ID: {row['id']}) does not contain valid audio bytes structure.")

if __name__ == "__main__":
    main()
