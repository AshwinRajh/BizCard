from PIL import Image, ImageDraw
import easyocr
import numpy as np
import PIL
import cv2
import os
import re
import pandas as pd
import sqlalchemy
import mysql.connector
from sqlalchemy import create_engine, inspect
import streamlit as st

# Main Page

# Comfiguring Streamlit GUI 
st.set_page_config(layout='wide')

# Title
st.markdown("<h1 style='text-align: center; font-size: 40px; color: red;' >Business Card Data Extraction </h1>", unsafe_allow_html=True)

# Tabs 
tab1, tab2 = st.tabs(["Data Extraction", "Data modification"])

# Data Extraction

with tab1:
    st.markdown("<h2 style='text-align: center; font-size: 25px; color: red;' >Data Extraction </h2>", unsafe_allow_html=True)


    # Image file uploaded
    import_image = st.file_uploader('Select a business card', type =['png','jpg', "jpeg"], accept_multiple_files=False)
    #  Data Extraction Begins...

    if import_image is not None:
        try:
            reader = easyocr.Reader(['en'], gpu=False)

        except:
            st.info("Error: easyocr module is not installed. Please install it.")

        try:
            if isinstance(import_image, str):
                image = Image.open(import_image)
            elif isinstance(import_image, Image.Image):
                image = import_image
            else:
                image = Image.open(import_image)
            
            image_array = np.array(image)
            text_read = reader.readtext(image_array)

            result = []
            for text in text_read:
                result.append(text[1])
                #Text_read willl be in the form of tuple and the second column gives the actual data.

        except:
            st.info("Error: Failed to process the image. Please try again with a different image.")

#Card processing with red boundaries
        col1, col2= st.columns(2)

        with col1:
            def draw_boxes(image, text_read, color='red', width=2):

                image_with_boxes = image.copy()
                draw = ImageDraw.Draw(image_with_boxes)
                
                for bound in text_read:
                    p0, p1, p2, p3 = bound[0]
                    draw.line([*p0, *p1, *p2, *p3, *p0], fill=color, width=width)
                return image_with_boxes

            result_image = draw_boxes(image, text_read)

            st.image(result_image, caption='Captured text')

#Data processing

        with col2:
            # Initialize the data dictionary
            data = {
                "Company_name": [],
                "Card_holder": [],
                "Designation": [],
                "Mobile_number": [],
                "Email": [],
                "Website": [],
                "Area": [],
                "City": [],
                "State": [],
                "Pin_code": [],
                }

            def get_data(res):
                city = ""  
                for ind, i in enumerate(res):
                   
                    if "www " in i.lower() or "www." in i.lower():
                        data["Website"].append(i)
                    elif "WWW" in i:
                        data["Website"].append(res[ind-1] + "." + res[ind])
                    elif "@" in i:
                        data["Email"].append(i)
                    elif "-" in i:
                        data["Mobile_number"].append(i)
                        if len(data["Mobile_number"]) == 2:
                            data["Mobile_number"] = " & ".join(data["Mobile_number"])
                    elif ind == len(res) - 1:
                        data["Company_name"].append(i)
                    elif ind == 0:
                        data["Card_holder"].append(i)
                    elif ind == 1:
                        data["Designation"].append(i)
                    if re.findall("^[0-9].+, [a-zA-Z]+", i):
                        data["Area"].append(i.split(",")[0])
                    elif re.findall("[0-9] [a-zA-Z]+", i):
                        data["Area"].append(i)
                    match1 = re.findall(".+St , ([a-zA-Z]+).+", i)
                    match2 = re.findall(".+St,, ([a-zA-Z]+).+", i)
                    match3 = re.findall("^[E].*", i)
                    if match1:
                        city = match1[0] 
                    elif match2:
                        city = match2[0]  
                    elif match3:
                        city = match3[0]  
                    state_match = re.findall("[a-zA-Z]{9} +[0-9]", i)
                    if state_match:
                        data["State"].append(i[:9])
                    elif re.findall("^[0-9].+, ([a-zA-Z]+);", i):
                        data["State"].append(i.split()[-1])
                    if len(data["State"]) == 2:
                        data["State"].pop(0)
                    if len(i) >= 6 and i.isdigit():
                        data["Pin_code"].append(i)
                    elif re.findall("[a-zA-Z]{9} +[0-9]", i):
                        data["Pin_code"].append(i[10:])

                data["City"].append(city)  
                
            get_data(result)

            data_df = pd.DataFrame(data)
            st.dataframe(data_df.T)

# MySql Begins
        # Create a session state object
        class SessionState:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        session_state = SessionState(data_uploaded=False)

        # Upload button
        st.write('Click the :red[**Upload to MySQL DB**] button to upload the data')
        Upload = st.button('**Upload to MySQL DB**', key='upload_button')

        if Upload:
            session_state.data_uploaded = True

        if session_state.data_uploaded:
            connect = mysql.connector.connect(
                host = "localhost",
                user = "root",
                password = "9524320874",    
                auth_plugin = "mysql_native_password")



            mycursor = connect.cursor()
            mycursor.execute("CREATE DATABASE IF NOT EXISTS bizcard_db")
            mycursor.close()
            connect.database = "bizcard_db"

            engine = create_engine('mysql+mysqlconnector://root:9524320874@localhost/bizcard_db', echo=True)

            try:
                data_df.to_sql('bizcardx_data', engine, if_exists='append', index=False, dtype={
                    "Company_name": sqlalchemy.types.VARCHAR(length=225),
                    "Card_holder": sqlalchemy.types.VARCHAR(length=225),
                    "Designation": sqlalchemy.types.VARCHAR(length=225),
                    "Mobile_number": sqlalchemy.types.String(length=50),
                    "Email": sqlalchemy.types.TEXT,
                    "Website": sqlalchemy.types.TEXT,
                    "Area": sqlalchemy.types.VARCHAR(length=225),
                    "City": sqlalchemy.types.VARCHAR(length=225),
                    "State": sqlalchemy.types.VARCHAR(length=225),
                    "Pin_code": sqlalchemy.types.String(length=10)})
                
                st.info('Data Successfully Uploaded')

            except:
                st.info("Card data already exists8")

            connect.close()

            session_state.data_uploaded = False

    else:
        st.info('Click the Browse file button and upload an image')

  #Modification zone

with tab2:

    col1,col2 = st.columns(2)
    with col1:
        st.subheader(':red[Edit option]')

        try:
            # Connect to the database
            conn = mysql.connector.connect(
                host = "localhost",
                user = "root",
                password = "9524320874",    
                auth_plugin = "mysql_native_password",
                database="bizcard_db")

            cursor = conn.cursor()

            # Execute the query to retrieve the cardholder data
            cursor.execute("SELECT card_holder FROM bizcardx_data")

            # Fetch all the rows from the result
            rows = cursor.fetchall()

            # Take the cardholder name
            names = []
            for row in rows:
                names.append(row[0])

            # Create a selection box to select cardholder name
            cardholder_name = st.selectbox("**Select a Cardholder name to Edit the details**", names, key='cardholder_name')

            # Collect all data depending on the cardholder's name
            cursor.execute( "SELECT Company_name, Card_holder, Designation, Mobile_number, Email, Website, Area, City, State, Pin_code FROM bizcardx_data WHERE card_holder=%s", (cardholder_name,))
            col_data = cursor.fetchone()

            # DISPLAYING ALL THE INFORMATION
            Company_name = st.text_input("Company name", col_data[0])
            Card_holder = st.text_input("Cardholder", col_data[1])
            Designation = st.text_input("Designation", col_data[2])
            Mobile_number = st.text_input("Mobile number", col_data[3])
            Email = st.text_input("Email", col_data[4])
            Website = st.text_input("Website", col_data[5])
            Area = st.text_input("Area", col_data[6])
            City = st.text_input("City", col_data[7])
            State = st.text_input("State", col_data[8])
            Pin_code = st.text_input("Pincode", col_data[9])

            # Create a session state object
            class SessionState:
                def __init__(self, **kwargs):
                    self.__dict__.update(kwargs)
            session_state = SessionState(data_update=False)
            
            # Update button
            st.write('Click the :red[**Update**] button to update the modified data')
            update = st.button('**Update**', key = 'update')

            # Check if the button is clicked
            if update:
                session_state.data_update = True

            # Execute the program if the button is clicked
            if session_state.data_update:

                # Update the information for the selected business card in the database
                cursor.execute(
                    "UPDATE bizcardx_data SET Company_name = %s, Designation = %s, Mobile_number = %s, Email = %s, "
                    "Website = %s, Area = %s, City = %s, State = %s, Pin_code = %s "
                    "WHERE Card_holder=%s",
                    (Company_name, Designation, Mobile_number, Email, Website, Area, City, State, Pin_code, Card_holder))
                
                conn.commit()

                st.success("successfully Updated.")

                # Close the database connection
                conn.close()
                
                session_state.data_update = False

        except:
            st.info('No data stored in the database')

#Delete option

    with col2:
        st.subheader(':red[Delete option]')

        try:
            # Connect to the database
            conn_del = mysql.connector.connect(
                host = "localhost",
                user = "root",
                password = "9524320874",    
                auth_plugin = "mysql_native_password",
                database="bizcard_db")

            # Execute the query to retrieve the cardholder data
            cursor = conn_del.cursor()
            cursor.execute("SELECT card_holder FROM bizcardx_data")

            # Fetch all the rows from the result
            del_name = cursor.fetchall()

            # Take the cardholder name
            del_names = []
            for row in del_name:
                del_names.append(row[0])

            # Create a selection box to select cardholder name
            delete_name = st.selectbox("**Select a Cardholder name to Delete the details**", del_names, key='delete_name')

            # Create a session state object
            class SessionState:
                def __init__(self, **kwargs):
                    self.__dict__.update(kwargs)
            session_state = SessionState(data_delet=False)

            # Delet button
            st.write('Click the :red[**Delete**] button to Delete selected Cardholder details')
            delet = st.button('**Delete**', key = 'delet')

            # Check if the button is clicked
            if delet:
                session_state.data_delet = True

            # Execute the program if the button is clicked
            if session_state.data_delet:
                cursor.execute(f"DELETE FROM bizcardx_data WHERE Card_holder='{delete_name}'")
                conn_del.commit()
                st.success("Successfully deleted from database.")

                # Close the database connection
                conn_del.close()

                session_state.data_delet = False

        except:
            st.info('No data stored in the database')
            
