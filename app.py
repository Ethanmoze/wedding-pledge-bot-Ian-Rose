import os
import io
from flask import Flask, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import json

app = Flask(__name__)

# NOTE: This code assumes you have a 'creds.json' file for Google Sheets API access
# and an 'arial.ttf' font file in the same directory.
# The template image 'Wedding_Template.png' MUST be in the 'static' directory.

# Google Sheets Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
try:
    # Use environment variable for credentials in a deployed environment
    creds_json = os.environ.get("GOOGLE_CREDS")
    if creds_json:
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    else:
        # Fallback to local file for development
        creds = ServiceAccountCredentials.from_json_keyfile_name("creds.json", scope)
    
    client = gspread.authorize(creds)
    sheet = client.open("Wedding Pledges").sheet1
except Exception as e:
    print(f"Error setting up Google Sheets: {e}")
    sheet = None # Set sheet to None to handle errors gracefully

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"]
        amount = request.form["amount"]
        contact = request.form["contact"]
        location = request.form["location"]
        message = request.form["message"]

        if sheet:
            try:
                sheet.append_row([name, amount, message, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), contact, location])
            except Exception as e:
                print(f"Error appending row to Google Sheet: {e}")

        # Create personalized card in memory
        template_path = os.path.join(app.root_path, "static", "Wedding_Template.png")
        
        try:
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"File not found: {template_path}")
            
            img = Image.open(template_path)
            draw = ImageDraw.Draw(img)

            # NOTE: You MUST have a font file named 'arial.ttf' in the same directory.
            font_path = os.path.join(app.root_path, "arial.ttf")
            
            try:
                font_large = ImageFont.truetype(font_path, 60)
                font_medium = ImageFont.truetype(font_path, 45)
            except IOError:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                print("Warning: arial.ttf not found, using default font. Font size will be fixed.")
            
            # --- FINAL ALIGNMENT ADJUSTMENTS ---
            # Adjusted coordinates for the name
            name_x_coord = 575
            name_y_coord = 310
            name_text = f"{name}"
            draw.text((name_x_coord, name_y_coord), name_text, fill="#6A5ACD", font=font_medium)

            # Adjusted coordinates for the pledge amount
            amount_x_coord = 570
            amount_y_coord = 750
            amount_text = f"{amount} UGX"
            draw.text((amount_x_coord, amount_y_coord), amount_text, fill="#9370DB", font=font_large)
            # --- END OF UPDATES ---
            
            # Save the image to an in-memory byte stream as a PNG
            img_io = io.BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)
            
            # Send the in-memory stream as a downloadable file
            return send_file(img_io, mimetype='image/png', as_attachment=True, download_name=f"pledge_{name.replace(' ', '_')}.png")

        except FileNotFoundError as e:
            print(f"Error: {e}")
            return render_template("index.html", error_message="Failed to create card. The template image file was not found.")
        except Exception as e:
            print(f"Error creating personalized card: {e}")
            return render_template("index.html", error_message="Failed to create card. Please try again.")

    return render_template("index.html")

