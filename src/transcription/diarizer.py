"""
Speaker diarisation and channel splitting for audio recordings.

Why this approach:
For stereo call recordings, we can assign speakers deterministically at zero compute cost:
Channel 0 maps to the Advisor, and Channel 1 maps to the Customer. We use the standard wave
library and numpy to split the channels. If the recording is mono, we process it as a single
stream and mark diarisation confidence as 'low', flagging it in the system.
"""

import os
import wave
import numpy as np
from typing import Tuple, Optional

def split_stereo_audio(filepath: str) -> Tuple[str, Optional[str], str]:
    """
    Analyzes a WAV file. If stereo, splits it into separate mono tracks for Advisor and Customer.
    If mono, falls back to returning the same file path with low diarisation confidence.
    
    Args:
        filepath (str): Path to the source WAV file.
        
    Returns:
        Tuple[str, Optional[str], str]: 
            - advisor_mono_path: Path to the Advisor audio file (or source if mono).
            - customer_mono_path: Path to the Customer audio file (or None if mono).
            - diarisation_confidence: 'high' for stereo, 'low' for mono.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Audio file not found: {filepath}")
        
    with wave.open(filepath, 'rb') as w_in:
        params = w_in.getparams()
        n_channels = params.nchannels
        
    if n_channels == 1:
        # Mono file fallback
        return filepath, None, "low"
        
    elif n_channels == 2:
        # Stereo file: split channels
        base_dir = os.path.dirname(filepath)
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        
        advisor_path = os.path.abspath(os.path.join(base_dir, f"{base_name}_advisor_mono.wav"))
        customer_path = os.path.abspath(os.path.join(base_dir, f"{base_name}_customer_mono.wav"))
        
        with wave.open(filepath, 'rb') as w_in:
            params = w_in.getparams()
            frames = w_in.readframes(params.nframes)
            
            # Determine data type based on sample width (PCM bit depth)
            if params.sampwidth == 2:
                dtype = np.int16
            elif params.sampwidth == 4:
                dtype = np.int32
            else:
                raise ValueError(f"Unsupported sample width: {params.sampwidth} bytes")
                
            data = np.frombuffer(frames, dtype=dtype)
            data = data.reshape(-1, 2)
            
            # Channel 0: Advisor
            advisor_data = data[:, 0].tobytes()
            mono_params = list(params)
            mono_params[0] = 1  # Set channel count to 1 (mono)
            
            with wave.open(advisor_path, 'wb') as w_out:
                w_out.setparams(mono_params)
                w_out.writeframes(advisor_data)
                
            # Channel 1: Customer
            customer_data = data[:, 1].tobytes()
            with wave.open(customer_path, 'wb') as w_out:
                w_out.setparams(mono_params)
                w_out.writeframes(customer_data)
                
        return advisor_path, customer_path, "high"
    else:
        raise ValueError(f"Unsupported channel count: {n_channels}")
