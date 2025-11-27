#!/usr/bin/env python3
"""
הפועל ירושלים כדורסל - מערכת הנהלת חשבונות
סקריפט הפעלה מהיר
"""

import sys
import subprocess
import os

def check_requirements():
    """בדיקת תלויות"""
    try:
        import flask
        import pandas
        import numpy
        import openpyxl
        print(" כל התלויות מותקנות")
        return True
    except ImportError as e:
        print(f" תלות חסרה: {e}")
        print(" מתקין תלויות...")

        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
            print(" התלויות הותקנו בהצלחה")
            return True
        except subprocess.CalledProcessError:
            print(" שגיאה בהתקנת תלויות")
            return False

def main():
    """פונקציה ראשית"""
    print(" הפועל ירושלים כדורסל - מערכת הנהלת חשבונות")
    print("=" * 60)

    # בדיקת תיקייה נוכחית
    if not os.path.exists('web_app.py'):
        print(" לא נמצא web_app.py בתיקייה הנוכחית")
        return

    # בדיקת תלויות
    if not check_requirements():
        return

    # הפעלת האפליקציה
    print("\n מפעיל את האפליקציה...")
    print(" כתובת: http://localhost:5001")
    print(" להפסיק: Ctrl+C")
    print("-" * 60)

    try:
        from web_app import app
        app.run(debug=True, host='localhost', port=5001)
    except KeyboardInterrupt:
        print("\nהאפליקציה נסגרה")
    except Exception as e:
        print(f"\n שגיאה: {e}")

if __name__ == "__main__":
    main()