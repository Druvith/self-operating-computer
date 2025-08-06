# Agent Tests

| Test Case | Observation | Time Taken | Possible Improvement |
|---|---|---|---|
| **Open a specific application (e.g., Calculator)** | Successfully opened the stocks app in MacOS using spotlight search. | 11.55s | None |
| **Search for a file on the system** | Successfully completed the task. | 11.62s |  |
| **Create a new text file and write to it** | Agent opened TextEditor using spotlight search. Identified the new doc button dimensions using EasyOCR. Wrote the text "Why did the scarecrow win an award? Because he was outstanding in his field!" (funny). | 46.12s  | speed-up the process from EasyOCR |
| **Open a web browser and navigate to a specific URL** | Additionally i'd prompted it open chrome in "guest mode". Task is successfully completed | 39.47s | None |
| **Search for something on Google** | Agent confuses itself when 2 windows are present on screen. Sometimes it defaults to "write" without being aware of the window or position of the cursor |  | Possibly prioritise to use OCR when 2 windows are present. Make sure "click & write" works|
| **Send an email using a web-based client** |  |  |  |
| **Find and play a specific video on YouTube** |  |  |  |
| **Create a new presentation in Google Slides** |  |  |  |
| **Create a new spreadsheet in Google Sheets** |  |  |  |
| **Post a message on a social media platform (e.g., Twitter)** |  |  |  |
