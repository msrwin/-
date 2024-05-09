import cv2
import numpy as np
import csv
import time
import os
from datetime import datetime
import math
import winsound

# カメラのキャプチャを開始
cap = cv2.VideoCapture(0)

# ファイルパスを設定
file_directory = "C:/Users/hinsyo/Desktop/ショア硬度計_データ取得/CSV"

# 現在の日付と時間を取得
current_datetime = datetime.now().strftime("%Y%m%d_%H-%M")

# 新しいファイル名を作成
new_file_name = f"SH_{current_datetime}.csv"
new_file_path = os.path.join(file_directory, new_file_name)

# CSVファイルへの書き込み回数を初期化
write_count = 0
paragraph_count = 1
last_time = time.time()  # 処理を開始する現在の時刻を記録

# 新しいCSVファイルを作成
with open(new_file_path, 'w', newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(['Frame', 'Value1', 'Value2', 'Value3', 'Value4', 'Value5'])

    # 1つのテストピースごとに値を保持するリストを初期化
    values_per_piece = []
    last_value = None  # last_valueを初期化
    
    while True:
        ret, frame = cap.read()

        if not ret:
            print("カメラからフレームを読み取れませんでした。")
            break

        current_time = time.time()
        if current_time - last_time >= 0.017:  # 1フレーム1/60秒、0.017秒ごとに値のチェック
            blurred = cv2.GaussianBlur(frame, (5, 5), 0)
            gray = cv2.cvtColor(blurred, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLinesP(edges, 1, np.pi/180, 50, minLineLength=100, maxLineGap=10)

            if lines is not None:
                max_line_length = 0
                selected_line = None

                for line in lines:
                    x1, y1, x2, y2 = line[0]
                    line_length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                    if line_length > max_line_length:
                        max_line_length = line_length
                        selected_line = line[0]

                if selected_line is not None:
                    x1, y1, x2, y2 = selected_line
                    line_theta = np.arctan2(y2 - y1, x2 - x1)
                    theta_deg = (np.degrees(line_theta) + 360) % 360  # 0～360度に正規化

                    if 0 <= theta_deg <= 155:
                        calculated_value = 70 + (theta_deg / 155) * 70 - 0.5 # 左半分の出力値微調整
                    elif 205 <= theta_deg <= 360:
                        calculated_value = 70 - ((360 - theta_deg) / 155) * 70 - 0.5 # 上に同じ

                    # 左半分だけを反時計回りに100度回転
                    if x1 < frame.shape[1] / 2:  # 左半分の場合
                        calculated_value = (calculated_value + 100) % 139.3  # 反時計回りに100度回転
                    else:  # 右半分の場合
                        if 155 <= theta_deg <= 360:
                            calculated_value = 70 - ((360 - theta_deg) / 155) * 70 + 40
                        elif 0 <= theta_deg <= 205:
                            calculated_value = 70 + (theta_deg / 100) * 70

                    if theta_deg > 89.8 and calculated_value < 70.2: # 70付近の異常な値を修正
                        last_value = 70
                    else:
                        last_value = calculated_value

                    if theta_deg > 270 and calculated_value < 30: # 30以下を正常に処理する
                        last_value = calculated_value
                    else:
                        last_value = calculated_value

            last_time = current_time  # 最終処理時間を更新する

        if last_value is not None:
            if selected_line is not None:
                cv2.line(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
            # カメラ画面に小数点以下1桁まで表示
            cv2.putText(frame, f"Value: {last_value:.1f}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Frame番号の表示
            frame_number = f"{paragraph_count} - {write_count % 5 + 1}"
            cv2.putText(frame, f"Frame: {frame_number}", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (200, 255, 0), 2)

        # 画面中央から上、左、右の端に青い点を描画 (カメラ角度調整用)
        center_x = frame.shape[1] // 2
        center_y = frame.shape[0] // 2
        cv2.circle(frame, (center_x, center_y - 200), 3, (255, 100, 100), -1)  # 上
        cv2.circle(frame, (center_x - 250, center_y), 3, (255, 100, 100), -1)  # 左
        cv2.circle(frame, (center_x + 250, center_y), 3, (255, 100, 100), -1)  # 右
        cv2.imshow('frame', frame)
        key = cv2.waitKey(1)
        
        if key == 27:  # ESCキーが押された場合
            break

        # ウィンドウが閉じられたかどうかを検出
        if cv2.getWindowProperty('frame', cv2.WND_PROP_VISIBLE) < 1:
            break

        elif key == 32:  # スペースキーが押された場合の処理
            winsound.Beep(500, 100)  # ピッと音を鳴らす
            # テストピースごとに値をリストに追加（四捨五入して小数点1桁にする）
            values_per_piece.append(round(last_value, 1))
            write_count += 1  # write_countはここで更新
            
            # 5回の計測ごとに値を書き込み、リストを初期化
            if len(values_per_piece) == 5:
                print(f"Number {paragraph_count}: {values_per_piece}")
                csv_writer.writerow([paragraph_count] + [round(value, 1) for value in values_per_piece])
                values_per_piece = []
                
                # Frame番号を更新
                if write_count % 5 == 0:
                    winsound.Beep(1000, 200)  # ピッと音を鳴らす
                    paragraph_count += 1         

cap.release()
cv2.destroyAllWindows()
