# Wings of Sounds API
<<<<<<< HEAD
The key entity we chose for our API is Venue since venue data will be the most essential component for our analysis. 

## Features
- CREATE non-existing venue(s) in the venues table by making a POST request through endpoint /venues/
- READ all venues in the venues table by making a GET request to endpoint /venues/
- READ a specific venue in the venues table by passing venue_id as an argument to endpoint /venues/{venue_id}
- UPDATE venue(s) in the venues table by making a PUT request to endpoint /venues/{venue_id}
- DELETE venue(s) in the venues table by making a DELETE request to endpoint /venues/{venue_id}

* API Documentation is available at http://localhost:8000/docs# (provided that you have followed the instructions below and start a local server)


## Prerequisites

- Python 3.11 or higher
- MySQL server, with appropriate host, username, password, database name
- pip (Python package manager)

## Setup

1. Clone the repository or download the source code.
   ```
   git clone https://github.com/projects-in-programming-f24/campy.git
   ```
   
2. Navigate to the project's directory

   (For Mac)
   ```
   cd path/to/wings
   ```
   (For Windows) 
   ```
   cd path\to\wings
   ```


3. Create a virtual environment
   ```
   python -m venv venv
   ```

4. Activate the Virtual Environment 

   (For Mac)
   ```
   source venv/bin/activate
   ```
   (For Windows)
   ```
   venv\Scripts\activate
   ```

5. Install the required packages
   ```
   pip install -r requirements.txt
   ```
 
6. Set up your .env file

   Create a new .env file in the project root directory

   (For Mac)
  
   ```
   touch .env
   ```
   (For Windows)
   ```
   type nul > .env
   ```

   Open the '.env' file in a text editor.

   Add the following your '.env' file and replace the placeholders with your actual MySQL connection details: 
   ```
   DB_HOST=my_mysql_host
   DB_USER=myuser
   DB_PASS=mypassword
   DB_NAME=my_database_name
   ```

   Save and close the '.env' file 

   Note: The `.env` file contains sensitive information. Make sure it's included in your `.gitignore` file to prevent it from being committed to version control.


 
## Usage

To run the application:

```
python3 main.py
```

Upon running the main.py script, your laptop is serving as a local server that listen for requests made locally. Ensure that your local server is active and running the entire time when you make requests to the API. To Create, Read, Update, or Delete a record from the 'venues' table, install Postman. After you have Postman installed, proceed to do the following: 
1. Open Postman
2. Click on New Request
3. Depending on which type of CRUD operation you would like to perform, select POST/PUT/CREATE/DELETE from the dropdown list next to the request URL field.
4. Input the URL according to the CRUD operation you would like to perform (endpoint available above in 'Features'). An example URL would be http://localhost:8001/endpoint.
5. Go to the Body tab and select raw and then JSON (or appropriate data type based on your API).
(If POST/ PUT request, Enter the JSON data you want to send to the API.)
6. Add any necessary headers, such as Content-Type: application/json
7. Click Send
8. Check the response to confirm if the data was created successfully. A 201 or 200 status code typically indicates success.









=======
The key entity we chose for our API is Venue since Venue data will be the most essential component for our analysis. The attributes include: <br /> 

id = string (unique identifier)<br />
name = string <br /> 
city = string<br />
zipcode = integer<br />
phone = integer<br />
capacity = integer<br />
style = list of strings (e.g. ["Theater","Performance Space"])<br />
keywords = list of strings (e.g. ["Intimate","Classy","Modern"])

The main advantage for building an API for our project is efficient data management. Having an API not only adds flexibility with functions to modify and remove data, but also allows reusability of the data. Additionally, it also provides a centralized access to Venue data and facilitates collaboration. 
>>>>>>> refs/remotes/origin/main
