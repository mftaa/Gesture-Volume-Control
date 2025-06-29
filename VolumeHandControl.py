import cv2
import time
import numpy as np
import HandTrackingModule as htm
import math
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

################################
wCam, hCam = 640, 480
################################

cap = cv2.VideoCapture(0)
cap.set(3, wCam)
cap.set(4, hCam)
pTime = 0

detector = htm.handDetector(detectionCon=0.7, maxHands=1)

devices = AudioUtilities.GetSpeakers()
interface = devices.Activate(
    IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
volume = cast(interface, POINTER(IAudioEndpointVolume))
volRange = volume.GetVolumeRange()

# --- VARIABEL BARU UNTUK PENGEMBANGAN ---
vol = 0
volBar = 400
volPer = 0
colorVol = (255, 0, 0)

# 1. Variabel untuk Kalibrasi
isCalibrated = False
calibrationTime = 8  # Kalibrasi selama 8 detik
startTime = 0
minHand, maxHand = 50, 220 # Nilai awal, akan di-update

print("Mempersiapkan kalibrasi... Posisikan tangan Anda di depan kamera.")
time.sleep(2)

while True:
    success, img = cap.read()

    # --- BLOK KALIBRASI DINAMIS ---
    if not isCalibrated:
        if startTime == 0:
            startTime = time.time()
        
        timeLeft = int(calibrationTime - (time.time() - startTime))
        if timeLeft < 0: timeLeft = 0
        
        # Tampilkan instruksi di layar
        cv2.putText(img, 'KALIBRASI', (180, 200), cv2.FONT_HERSHEY_COMPLEX, 1.5, (0, 255, 0), 3)
        cv2.putText(img, f'Gerakkan Jari dari Jarak Terdekat ke Terjauh', (30, 250), cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 255), 2)
        cv2.putText(img, f'Waktu: {timeLeft}s', (240, 300), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 2)

        img_no_draw = detector.findHands(img, draw=False)
        lmList, bbox = detector.findPosition(img_no_draw, draw=False)

        if len(lmList) != 0:
            length, _, _ = detector.findDistance(4, 8, img_no_draw, draw=False)
            if length < minHand: minHand = length
            if length > maxHand: maxHand = length
        
        if time.time() - startTime > calibrationTime:
            isCalibrated = True
            minHand = int(minHand + 15) # Tambah margin
            maxHand = int(maxHand - 15) # Kurangi margin
            print(f"Kalibrasi Selesai. Rentang Jarak: [{minHand}, {maxHand}]")
            if minHand >= maxHand: # Jika kalibrasi gagal, gunakan default
                minHand, maxHand = 50, 220
                print("Kalibrasi gagal, menggunakan nilai default.")
            
        cv2.imshow("Img", img)
        cv2.waitKey(1)
        continue # Lanjutkan ke frame berikutnya sampai kalibrasi selesai

    # --- LOGIKA UTAMA SETELAH KALIBRASI ---
    img = detector.findHands(img)
    lmList, bbox = detector.findPosition(img, draw=False) # Gambar bbox nanti
    bboxColor = (0, 0, 255)  # Default: Merah (tidak aktif)

    if len(lmList) != 0:
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) // 100
        
        if 250 < area < 1000:
            bboxColor = (0, 255, 0) # Hijau (aktif)
            
            length, img, lineInfo = detector.findDistance(4, 8, img)

            volBar = np.interp(length, [minHand, maxHand], [400, 150])
            volPer = np.interp(length, [minHand, maxHand], [0, 100])
            
            smoothness = 5
            volPer = smoothness * round(volPer / smoothness)

            fingers = detector.fingersUp()
            
            if not fingers[4]: # Pemicu: kelingking turun
                # 2. Logika Mute/Unmute
                if length < minHand:
                    if not volume.GetMute():
                        volume.SetMute(True, None)
                        print("Muted")
                        time.sleep(0.2)
                    cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (0, 0, 255), cv2.FILLED)
                else:
                    if volume.GetMute():
                        volume.SetMute(False, None)
                        print("Unmuted")
                    volume.SetMasterVolumeLevelScalar(volPer / 100, None)
                    cv2.circle(img, (lineInfo[4], lineInfo[5]), 15, (0, 255, 0), cv2.FILLED)
                    colorVol = (0, 255, 0)
            else:
                colorVol = (255, 0, 0)

        # 3. Gambar Bounding Box dengan warna dinamis
        cv2.rectangle(img, (bbox[0] - 20, bbox[1] - 20), (bbox[2] + 20, bbox[3] + 20), bboxColor, 2)

    # Drawings
    cv2.rectangle(img, (50, 150), (85, 400), (255, 0, 0), 3)
    cv2.rectangle(img, (50, int(volBar)), (85, 400), (255, 0, 0), cv2.FILLED)
    cv2.putText(img, f'{int(volPer)} %', (40, 450), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 0, 0), 3)
    
    cVol = int(volume.GetMasterVolumeLevelScalar() * 100)
    if volume.GetMute():
        cv2.putText(img, f'Vol Set: MUTED', (350, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 0, 255), 3)
    else:
        cv2.putText(img, f'Vol Set: {int(cVol)}', (350, 50), cv2.FONT_HERSHEY_COMPLEX, 1, colorVol, 3)

    # Frame rate
    cTime = time.time()
    fps = 1 / (cTime - pTime)
    pTime = cTime
    cv2.putText(img, f'FPS: {int(fps)}', (40, 50), cv2.FONT_HERSHEY_COMPLEX, 1, (255, 0, 0), 3)

    cv2.imshow("Img", img)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()