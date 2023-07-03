import tkinter as tk
import customtkinter as ctk
from tkinter import messagebox
import cv2
from PIL import Image, ImageTk
import numpy as np
import face_recognition
import os
import mysql.connector
from tkinter import ttk
import datetime
import tempfile
import base64
import subprocess

# Database connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="123",
    database="dbmain",
    auth_plugin='mysql_native_password'
)
cursor = conn.cursor()

facesImg = 'cpeStudents'
images = []
studentNames = []
myList = os.listdir(facesImg)

for cl in myList:
    currentImage = cv2.imread(f'{facesImg}/{cl}')
    images.append(currentImage)
    studentNames.append(os.path.splitext(cl)[0])

print(studentNames)

def findEncodings(images):
    encodeList = []
    for img in images:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        encode = face_recognition.face_encodings(img)[0]
        encodeList.append(encode)
    return encodeList

encodeListKnown = findEncodings(images)
print('Encoding Complete')

def showFrame():
    _, img = cap.read()  # Read a frame from the camera
    imgSmall = cv2.resize(img, None, fx=0.25, fy=0.25)
    imgSmall = cv2.cvtColor(imgSmall, cv2.COLOR_BGR2RGB)

    facesCurrentFrame = face_recognition.face_locations(imgSmall)
    encodesCurrentFrame = face_recognition.face_encodings(imgSmall, facesCurrentFrame)

    if len(facesCurrentFrame) == 0:
        button.configure(state = "disabled")
        
        #Add text
        text = "     Align your face properly & Stay Still"
        textWidth, textHeight = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)[0]
        textX = (img.shape[1] - textWidth) // 2
        textY = (img.shape[0] + textHeight) // 2

        # Add black rectangle behind the text
        rectWidth = textWidth + 20
        rectHeight = textHeight + 20
        rectX = (img.shape[1] - rectWidth) // 2
        rectY = (img.shape[0] - rectHeight) // 2
        cv2.rectangle(img, (rectX, rectY), (rectX + rectWidth, rectY + rectHeight), (0, 0, 0, 0), cv2.FILLED)
        cv2.putText(img, text, (textX, textY), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    else:
        button.configure(state = "normal")

    for encodeFace, faceLoc in zip(encodesCurrentFrame, facesCurrentFrame):
        faceMatched = face_recognition.compare_faces(encodeListKnown, encodeFace)
        faceDistance = face_recognition.face_distance(encodeListKnown, encodeFace)
        print(faceDistance)
        global matchIndex
        matchIndex = np.argmin(faceDistance)
        
        if faceMatched[matchIndex]:
            global name 
            name = studentNames[matchIndex].upper()
            print(name)
            y1, x2, y2, x1 = faceLoc
            y1, x2, y2, x1 = y1 * 4, x2 * 4, y2 * 4, x1 * 4
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.rectangle(img, (x1, y2 - 35), (x2, y2), (0, 0, 0), cv2.FILLED)
            cv2.putText(img, name, (x1 + 6, y2 - 6), cv2.FONT_HERSHEY_COMPLEX, 0.8, (255, 255, 255), 1)

            # Insert or update data in the database
            global currentTime 
            currentTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Save the current frame as a temporary image file
            tempFile = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
            cv2.imwrite(tempFile.name, img)

            # Read the image file and encode it as base64
            with open(tempFile.name, "rb") as f:
                global encodedImage
                encodedImage = base64.b64encode(f.read())

    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Convert frame colors from BGR to RGB
    img = cv2.resize(img, (640, 480))  # Resize the frame to fit within the Tkinter window
    img = ImageTk.PhotoImage(image=Image.fromarray(img))  # Create a PIL ImageTk instance

    label.config(image=img)  # Update the image in the label
    label.image = img

    label.after(10, showFrame)  # Call the show_frame function again after 10 milliseconds

def onClosing():
    # Release the camera and close the OpenCV window
    cap.release()
    cv2.destroyAllWindows()
    conn.close()
    window.destroy()

# Initialize the Tkinter window
ctk.set_appearance_mode("System")
window = ctk.CTk()
window.title("AttendEase")
window.geometry("1080x480+560+240")
window.resizable(False, False)
window.iconbitmap("logo2.ico")

# Create a frame to hold the video feed
frame = tk.Frame(window, width=540, height=700, bg="#1a1a1a")
frame.place(x=10, y=10)

# Create a label to display the video feed
label = tk.Label(frame, bd=10,  background="#1a1a1a")
label.pack()

# Open the camera
cap = cv2.VideoCapture(1)

# Register the window closing event handler
window.protocol("WM_DELETE_WINDOW", onClosing)

# Create an Attend button
button = ctk.CTkButton(window, text="ATTEND", width= 250, height = 50, fg_color = "#6aa51f", hover_color="#406313")
button.place(x= 150, y = 420)

# Create a table
tableFrame = tk.Frame(window)
tableFrame.place(x = 700, y = 20)

style = ttk.Style()
style.configure("Treeview.Heading", font=("Arial", 12, "bold"))
style.configure("Custom.Treeview", font=("Arial", 10, "bold"), foreground = "white", background="#1a1e26")

table = ttk.Treeview(tableFrame, columns=("ID", "Name", "Date & Time"), show="headings", style="Custom.Treeview")
table.configure(height=23)

table.heading("ID", text="ID")
table.heading("Name", text="Name")
table.heading("Date & Time", text="Date & Time")
table.configure(style="Custom.Treeview")
table.pack()

# Fetch data from the database and populate the table
def fetchData(tableName):
    table.delete(*table.get_children())  # Clear existing data in the table
    cursor.execute(f"SELECT * FROM {tableName}")
    rows = cursor.fetchall()
    for row in rows:
        table.insert("", tk.END, values=row)

    # Insert or update data in the database with the snapshot
    cursor.execute(f"INSERT INTO {currentTableName} (ID, Name, Date_N_Time, Snapshot) "
                    "VALUES (%s, %s, %s, %s) "
                    "ON DUPLICATE KEY UPDATE Name=VALUES(Name), Date_N_Time=VALUES(Date_N_Time), Snapshot=VALUES(Snapshot)",
                    (int(matchIndex) + 1, name, currentTime, encodedImage))
    conn.commit()

# Bind the button click event to fetchData function
button.configure(command=lambda: fetchData(currentTableName))

# Create a "New Table" button
newTableButton = ctk.CTkButton(window, text="+  New Table")
newTableButton.place(x = 570 , y = 430)

#Create a "See Images" button
seeImagesButton = ctk.CTkButton(window, text="See Images")
seeImagesButton.place(x=890, y =430)

# Track the current table index
currentTableIndex = 1
currentTableName = "attendance"

# Function to create a new table in the database and update the displayed table
def createNewTable():
    def authenticate():
        username = username_entry.get()
        password = password_entry.get()

        # Check the username and password
        if username == "admin" and password == "password":
            global currentTableIndex
            global currentTableName

            # Increment the table index and create the new table name
            currentTableIndex += 1
            currentTableName = f"attendance_new_{currentTableIndex}"

            # Create a new table
            cursor.execute(f"CREATE TABLE IF NOT EXISTS {currentTableName} (ID INT, Name VARCHAR(255), Date_N_Time VARCHAR(255), Snapshot LONGBLOB, PRIMARY KEY (ID))")
            conn.commit()

            # Clear the table widget
            table.delete(*table.get_children())

            # Update the button text and command
            button.configure(text="ATTEND", command=lambda: fetchData(currentTableName))
            auth.destroy()
        else:
            messagebox.showerror("Authentication Failed", "Invalid username or password.")

    # Create the authentication window
    ctk.set_appearance_mode("System")
    auth = ctk.CTk()
    auth.title("Authentication")
    auth.geometry("300x160")
    auth.resizable(False, False)
    auth.iconbitmap("logo2.ico")

    # Create the username label and entry
    username_label = ctk.CTkLabel(auth, text="Username:")
    username_label.pack()
    username_entry = ctk.CTkEntry(auth)
    username_entry.pack()

    # Create the password label and entry
    password_label = ctk.CTkLabel(auth, text="Password:")
    password_label.pack()
    password_entry = ctk.CTkEntry(auth, show="*")
    password_entry.pack()

    # Create the authenticate button
    authenticate_button = ctk.CTkButton(auth, text="Authenticate", command=authenticate, fg_color = "#6aa51f", hover_color="#406313")
    authenticate_button.place(x = 80, y = 125)

    # Start the Tkinter event loop
    auth.mainloop()


#Function to see captured Images in the database
def runPyFile():
    # Path to the virtual environment's Python executable
    venvPython = r'C:/Users/danil/OneDrive/Desktop/retrieveImgApp/venv/Scripts/python.exe'

    # Path to the retrieveImg.py script
    scriptPath = r'C:/Users/danil/OneDrive/Desktop/retrieveImgApp/retrieveImg.py'

    # Command to execute the script within the virtual environment
    command = [venvPython, scriptPath]

    # Execute the command
    subprocess.run(command, check=True)

# Bind the button click event to createNewTable function
newTableButton.configure(command=createNewTable)

# Bind the button click event to runPyFile function
seeImagesButton.configure(command=runPyFile)

# Start displaying frames
showFrame()

# Start the Tkinter event loop
window.mainloop()
