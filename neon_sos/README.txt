HOLOGRAM SOS - NEON SMARTWATCH SIMULATION
==========================================
Module of: "A Context-Aware Self-Transforming Smartwatch Interface
            for Emergency Response and Secure Payments"

SIMULATION ONLY. No real GPS, calls, SMS or internet are used.

FILES
-----
  sos_watch.py   the whole program (one file, standard Python only)
  contacts.txt   dummy emergency contacts:  Name, phone, relation
  README.txt     this file

Created automatically when you use the program (safe to delete):
  sos_log.txt     every event with date and time
  sos_outbox.txt  every simulated alert message (Transmitted: NO)

REQUIREMENTS
------------
  Python 3 from python.org (tested with Python 3.14.6, Tk 9.0).
  Nothing to install - tkinter is part of the standard Windows installer.

HOW TO RUN (Windows, VS Code terminal / PowerShell)
---------------------------------------------------
  cd "path\to\neon_sos"
  py sos_watch.py

HOW TO USE
----------
  1. Press and HOLD the red SOS button for 1 second.
     The cyan ring fills up while you hold. Letting go early, or dragging
     the mouse off the button, stops it (protects against accidents).
  2. A 5-second countdown starts. Click CANCEL (or press Esc) to stop it.
     The watch shows "SOS CANCELLED" and returns to the normal screen.
  3. If you do not cancel, SOS ACTIVE mode starts: simulated location,
     simulated alerts for every contact, and the time of activation.
  4. Click RESET on the watch to return to normal.
  5. Click UPDATE LOCATION on the dashboard at any time to simulate a
     new GPS reading.

SETTINGS (top of sos_watch.py)
------------------------------
  HOLD_SECONDS = 1             hold time needed to trigger SOS
  COUNTDOWN_SECONDS = 5        time allowed to cancel
  TRIGGER_FLASH_SECONDS = 0.5  short "SOS TRIGGERED" flash
  CANCEL_MESSAGE_SECONDS = 2   how long "SOS CANCELLED" is shown
  BASE_LATITUDE / BASE_LONGITUDE   sample location
