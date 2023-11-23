from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.db import IntegrityError
from datetime import datetime
from django.shortcuts import render, redirect
from django.db import connection
from django.contrib.auth.hashers import make_password
import uuid
from django.contrib import messages
from django.http import Http404
import openai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access the API key
api_key = os.getenv('MY_API_KEY')

cur_user = {}


def testmysql(request):
    # with connection.cursor() as cursor:
    #     cursor.execute("""
    #         select VIN
    #         from LISTED_VEHICLES
    #     """)

    #     rows = cursor.fetchall()

    user_type = request.session.get('user_type', '')
    user_name = request.session.get('user_name', '')

    context = {
        'user_type': user_type,
        'user_name': user_name,
    }
    return render(request, 'home.html', context)


def register(request):
    if request.method == "POST":
        try:
            # Get data from POST request
            user_type = request.POST.get('user_type', '')
            user_name = request.POST.get('user_name', '')
            email = request.POST.get('email', '')

            # Insert data into the database
            with connection.cursor() as cursor:
                query = """
                    INSERT INTO USERS (user_type, user_name, email)
                    VALUES (%s, %s, %s);
                """
                cursor.execute(query, (user_type, user_name, email))
                connection.commit()
                return redirect('home')
        except Exception as e:
            # Handle any errors that occur during the process
            print(f"An error occurred: {e}")
            # Optionally, add error handling logic here (e.g., set an error message, rollback transaction)

    # Render the registration form for both GET and POST requests
    return render(request, 'register.html')


def login(request):
    if request.method == "POST":
        try:
            # Get data from POST request
            user_email = request.POST.get('email', '')

            # Query the database
            with connection.cursor() as cursor:
                query = """
                    SELECT *
                    FROM USERS
                    WHERE email = %s;
                """
                cursor.execute(query, [user_email]
                               )  # Pass parameters as a list
                t = cursor.fetchall()
                if not t:
                    return render(request, 'error.html')
                else:
                    # return render(request, "home.html", context)
                    cur_user = t
                    print(cur_user)
                    user_data = t[0]
                    user_type = user_data[1]
                    user_name = user_data[2]
                    request.session['user_type'] = user_type
                    request.session['user_name'] = user_name
                    return redirect('home')
        except Exception as e:
            # Handle any errors that occur during the process
            print(f"An error occurred: {e}")
            # Optionally, add error handling logic here

    # Render the login form for GET requests
    return render(request, 'login.html')


def logout(request):
    request.session.flush()
    return redirect('home')


def profile(request):

    return render(request, 'profile.html')


def search_car(request):
    # Fetch unique values for dropdowns from the database
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT DISTINCT make FROM LISTED_VEHICLES ORDER BY make")
        makes = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            "SELECT DISTINCT year_of_production FROM LISTED_VEHICLES ORDER BY year_of_production")
        years = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            "SELECT DISTINCT mileage FROM LISTED_VEHICLES ORDER BY mileage")
        mileages = [row[0] for row in cursor.fetchall()]

        cursor.execute(
            "SELECT DISTINCT price FROM LISTED_VEHICLES ORDER BY price")
        prices = [row[0] for row in cursor.fetchall()]

    error_message = None

    # Fetch filter parameters
    make = request.GET.get('make')
    min_year = request.GET.get('min_year')
    max_year = request.GET.get('max_year')
    min_mileage = request.GET.get('min_mile')
    max_mileage = request.GET.get('max_mile')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')

    # Check for invalid filter ranges
    if min_year and max_year and int(min_year) > int(max_year):
        error_message = "Minimum year cannot be greater than maximum year."
    elif min_mileage and max_mileage and int(min_mileage) > int(max_mileage):
        error_message = "Minimum mileage cannot be greater than maximum mileage."
    elif min_price and max_price and int(min_price) > int(max_price):
        error_message = "Minimum price cannot be greater than maximum price."

    # If there's an error, return early with the error message
    if error_message:
        return render(request, 'search_car.html', {'error_message': error_message})

# Initialize the base query
    query = "SELECT * FROM LISTED_VEHICLES WHERE listing_status = TRUE"

    # Initialize the parameters list
    params = []

    # Append conditions to the query based on provided filters
    if make:
        query += " AND make = %s"
        params.append(make)

    if min_year:
        query += " AND year_of_production >= %s"
        params.append(min_year)

    if max_year:
        query += " AND year_of_production <= %s"
        params.append(max_year)

    if min_mileage:
        query += " AND mileage >= %s"
        params.append(min_mileage)

    if max_mileage:
        query += " AND mileage <= %s"
        params.append(max_mileage)

    if min_price:
        query += " AND price >= %s"
        params.append(min_price)

    if max_price:
        query += " AND price <= %s"
        params.append(max_price)

    # Fetch the search term
    search_words = []
    search_term = request.GET.get('search_term', '').strip()

    # Check if search term is not empty
    if search_term:
        search_words = search_term.split()

    # Initialize search_words as an empty list
    search_words = []

    # Fetch the search term
    search_term = request.GET.get('search_term', '').strip()

    # Check if search term is not empty
    if search_term:
        search_words = search_term.split()

        # Build the search query only if there are search words
        search_query = " AND ("
        search_query_parts = []
        for word in search_words:
            search_query_parts.append(
                "(make LIKE %s OR model LIKE %s OR exterior_color LIKE %s OR "
                "vehicle_description LIKE %s OR fuel_type LIKE %s OR CAST(year_of_production AS CHAR) LIKE %s)")
            params.extend(["%" + word + "%"] * 6)

        # Only append if there are parts to the search query
        if search_query_parts:
            search_query += " OR ".join(search_query_parts) + ")"
            query += search_query

    vehicles = []
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        for row in cursor.fetchall():
            vehicles.append(dict(zip(columns, row)))

    return render(request, 'search_car.html', {
        'vehicles': vehicles,
        'makes': makes,
        'years': years,
        'mileages': mileages,
        'prices': prices,
        'error_message': error_message
    })


def product_detail(request, listing_id):
    result = None
    current_bid = None

    with connection.cursor() as cursor:
        # SQL query to join USERS and LISTED_VEHICLES tables
        cursor.execute("""
            SELECT LV.*, U.*
            FROM LISTED_VEHICLES AS LV
            JOIN USERS AS U ON LV.seller_id = U.user_id
            WHERE LV.listing_id = %s
        """, [listing_id])

        result = cursor.fetchone()

    # If no product is found, raise a 404 error
    if not result:
        raise Http404("Product does not exist")

    # Check if the current user has bid on this product

    # need modification
    # hardcoded
    current_user_id = 2
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT bidding_amount FROM BIDDINGS
            WHERE listing_id = %s AND user_id = %s
            ORDER BY bidding_date DESC
            LIMIT 1
        """, [listing_id, current_user_id])
        current_bid = cursor.fetchone()

    # Map the result to a dictionary for easy access in the template
    product_dict = {
        'listing_id': result[0],
        'VIN': result[2],
        'image_url': result[4],
        'vehicle_description': result[5],
        'make': result[6],
        'model': result[7],
        'fuel_type': result[8],
        'year_of_production': result[9],
        'mileage': result[10],
        'price': result[11],
        'exterior_color': result[12],
        'interior_color': result[13],
        'state': result[14],
        'zip_code': result[15],
        'seller_name': result[22],
        'seller_rating': result[25],
        'current_bid': current_bid[0] if current_bid else None,
    }

    # return render(request, 'product_detail.html', {'product': product_dict})
    if request.method == 'POST':
        bid_amount = request.POST.get('bid_amount')
        # Assuming user authentication
        user_id = request.user.id

        # Convert bid amount to a decimal or float as needed
        bid_amount = float(bid_amount)

        # Insert the bid into the database
        with connection.cursor() as cursor:
            cursor.execute("""
                INSERT INTO BIDDINGS (listing_id, user_id, bidding_amount, bidding_date)
                VALUES (%s, %s, %s, NOW())
            """, [listing_id, user_id, bid_amount])
            # If the bid is successfully placed, add a success message
            messages.success(request, 'Bid placed successfully!')
            # Redirect to the same page to display the success message
            return redirect('bid_success', listing_id=listing_id, user_id=request.user.id)
        # If the bid is not successful, you might want to add an error message and
        # handle it accordingly

    # For GET requests or if the bid placement is not successful, render the page with product details
    return render(request, 'product_detail.html', {'product': product_dict})


def bid(request, listing_id):
    if request.method == 'POST':
        try:
            bid_amount = float(request.POST['bid_amount'])

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT price FROM LISTED_VEHICLES WHERE listing_id = %s", [listing_id])
                product_price = cursor.fetchone()
                if not product_price or bid_amount < product_price[0]:
                    # Handle bid amount lower than product price
                    return render(request, 'error.html', {'error_message': 'Bid amount must be higher than the product price'})

                cursor.execute("SELECT MAX(bidding_id) FROM BIDDINGS")
                max_id_result = cursor.fetchone()
                new_bidding_id = max_id_result[0] + \
                    1 if max_id_result[0] else 1

                cursor.execute("""
                    INSERT INTO BIDDINGS (bidding_id, listing_id, user_id, bidding_amount, bidding_date, is_winner)
                    VALUES (%s, %s, 2, %s, %s, %s)
                """, [new_bidding_id, listing_id, bid_amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), False])
                connection.commit()

            return redirect('product_detail', listing_id=listing_id)
        except IntegrityError as e:
            print(e)
            # Handle the error, perhaps show a message to the user

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT LV.*, U.*
            FROM LISTED_VEHICLES AS LV
            JOIN USERS AS U ON LV.seller_id = U.user_id 
            WHERE LV.listing_id = %s
        """, [listing_id])

        result = cursor.fetchone()

    product_dict = {
        # Assuming these indices are correct
        'image_url': result[4],
        'make': result[6],
        'model': result[7],
        'price': result[11],
    }

    return render(request, 'bid.html', {'product': product_dict, 'listing_id': listing_id})


def bid_success(request, listing_id):
    # need modification
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT *
            FROM BIDDINGS 
            WHERE listing_id = %s
        """, [listing_id])

        result = cursor.fetchone()

    # Map the result to a dictionary for easy access in the template
    bidding_dict = {
        'bidding_amount': result[3],
    }

    return render(request, 'bid.html', {'bidding': bidding_dict})

# views.py


def chatbot(request):
    # Render the chat interface page
    return render(request, 'chatbot.html')


@csrf_exempt
@require_POST
def chat(request):
    data = json.loads(request.body)
    user_message = data.get('message')

    # You need to configure your OpenAI API key
    openai.api_key = api_key

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}]
        )
        return JsonResponse({'response': response.choices[0].message['content']})
    except Exception as e:
        return JsonResponse({'response': str(e)}, status=500)
