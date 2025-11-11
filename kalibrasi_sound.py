import pyaudio
import numpy as np
import time
import sys

# --- Konfigurasi Audio (WAJIB SAMA dengan app utama) ---
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
# --------------------------------------------------------

audio = None
stream = None

try:
    # 1. Inisialisasi PyAudio
    audio = pyaudio.PyAudio()
    print("PyAudio diinisialisasi...")

    # 2. Buka Stream
    stream = audio.open(format=FORMAT, 
                        channels=CHANNELS,
                        rate=RATE, 
                        input=True,
                        frames_per_buffer=CHUNK)

    print("\n" + "=" * 50)
    print("--- SKRIP KALIBRASI KONTINU (REAL-TIME) ---")
    print("Skrip ini akan terus menampilkan Amplitudo RMS mentah.")
    print("\n📋 TUGAS ANDA:")
    print(" 1. Siapkan sumber suara Anda (misal: nada 1kHz).")
    print(" 2. Lihat layar GM1356 Anda. Tunggu hingga stabil (misal: 60.3 dB).")
    print(" 3. Lihat angka 'Amplitudo RMS' di terminal ini. Tunggu hingga stabil.")
    print(" 4. CATAT PASANGANNYA (misal: [0.3055, 60.3]).")
    print(" 5. Ulangi untuk level suara yang berbeda.")
    print("\nTekan Ctrl+C untuk BERHENTI jika sudah selesai.")
    print("=" * 50)

    # 3. Mulai stream
    stream.start_stream() 
    
    # Beri waktu 1 detik untuk pemanasan
    print("\nMemulai stream... (tunggu 1 detik)")
    time.sleep(1)
    print("STREAM AKTIF. Mulai membaca data:\n")
    
    while True:
        try:
            # 4. Baca data
            data = stream.read(CHUNK)
            
            # 5. Proses data
            numpy_data = np.frombuffer(data, dtype=np.int16)
            normalized_data = numpy_data / 32768.0
            rms_amplitude = np.sqrt(np.mean(normalized_data**2))
            
            # 6. Cetak hasil ke baris yang sama (menggunakan '\r')
            # .ljust(40) memastikan baris lama terhapus bersih
            print(f"  Amplitudo RMS Mentah: {rms_amplitude:.4f}".ljust(40), end='\r')
            
            # 7. Beri jeda sedikit agar CPU tidak 100% dan output terbaca
            time.sleep(0.05) # Cetak ~20x per detik

        except IOError:
            # Jika buffer overflow, lewati saja dan lanjut
            print("Peringatan: Buffer overflow, data dilewati.".ljust(40), end='\r')
            continue

except KeyboardInterrupt:
    # 8. Jika pengguna menekan Ctrl+C
    print("\n\nProses kalibrasi dihentikan oleh pengguna.")
    
except Exception as e:
    print(f"\nTERJADI KESALAHAN: {e}")
    print("Pastikan microphone/line-in terhubung dan diizinkan.")
    
finally:
    # 9. Selalu bersihkan
    print("Menutup stream dan PyAudio...")
    if stream:
        if stream.is_active():
            stream.stop_stream()
        stream.close()
    if audio:
        audio.terminate()
    print("Selesai. Selamat mencatat data.")