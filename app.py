import numpy
from flask import Flask, render_template, request, redirect, url_for, json
import sqlite3 as sql
import numpy as np
from datetime import datetime
# hash

from passlib.hash import sha256_crypt

app = Flask(__name__)


# login section
@app.route('/')
def login_redirect():
    return redirect('/login')#redirects to login in page

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == "GET":
        return render_template('login.html', f_status=0)  # sets failed status of html
    if request.method =="POST":
        global email
        email =  request.form['email_entry']
        password = sha256_crypt.encrypt(request.form['password_entry']);
        valid =login_validation(email, password)
        if valid == 1:
            return redirect('/seller')#redirect to seller
        elif valid == 2:
            return redirect('/buyer') #redirect to buyer
        else:
            return render_template('login.html', f_status = 1) # sets failed status of html

def login_validation(email, password):
    connection = sql.connect('NM_database.db')
    connection.execute('CREATE TABLE IF NOT EXISTS users(email TEXT, password TEXT, PRIMARY KEY(email));')
    #get password to login
    cor_pas = connection.execute('SELECT password FROM users WHERE email = ?;', [email] ).fetchone()
    if cor_pas == None: #index the password from the tuple object
        return 0
    #cmp passwords to login
    cor_pas= cor_pas[0]
    if sha256_crypt.verify(cor_pas, password) == False:
        return 0
    #check if Seller
    is_seller =connection.execute('SELECT email FROM Sellers WHERE email = ?;', [email] ).fetchall()
    if is_seller != []:
        return 1; #is seller
    else:
        return 2 # is Buyer

#Buyer functionaility
@app.route('/buyer', methods=["GET" ,"POST"])
def buyers_page():
    connection = sql.connect('NM_database.db')
    is_seller = connection.execute('SELECT email FROM Sellers WHERE email = ?;', [email]).fetchall()
    seller = "false"
    if is_seller != []:
        seller = "true"
    return render_template('buyer_home.html', seller = seller)

@app.route('/buyer/product_search', methods=["POST"])
def buyer_product_search():
        return product_search("buyer")

@app.route('/buyer/checkout', methods =["POST"])
def checkout():
    global product
    connection = sql.connect('NM_database.db')
    cc_nums = connection.execute('SELECT credit_card_num  FROM Credit_Cards WHERE Owner_email =?;',
                                 [email]).fetchall()
    if request.form["submit"] == "move":
        seller_email = request.form["seller_email"]
        listing_ID = int(request.form["listing_ID"])
        quantity = int(request.form["quantity"])
        product = connection.execute('Select * FROM Product_Listing WHERE Listing_ID =? AND Seller_Email = ? collate NOCASE;', [listing_ID, seller_email]).fetchall()
        product = np.asarray(product).flatten()
        return render_template('buyer_checkout.html', product = product, quantity= quantity, cc_nums = cc_nums)
    if request.form["submit"] == "confirm":
        quantity = int(request.form["Quantity"])
        if int(product[7])< quantity:
            return render_template('buyer_checkout.html', product = product, cc_nums = cc_nums, mes ="INVALID QUANTITY")
        date = datetime.now().strftime("%m/%d/%Y")
        cc = request.form["cc_sel"]
        trans_id = 1;
        trans_id_list =connection.execute('Select Transaction_ID FROM ORDERS;').fetchall()
        trans_id_list = np.asarray(trans_id_list).flatten()
        # print(trans_id_list)
        while trans_id in trans_id_list:
            # print(trans_id)
            trans_id = trans_id +1
        connection.execute(
            'INSERT INTO ORDERS (Transaction_ID, Seller_Email, Listing_ID, buyer_email,date, quantity, payment) VALUES (?,?,?,?,?,?,?);',
            (trans_id, product[0], product[2], email,date, quantity, cc))
        new_q = int(product[7]) -quantity
        connection.execute('UPDATE Product_Listing SET quantity = ? WHERE Seller_Email = ? AND Listing_ID =?;', [new_q, product[0], product[1]])
        connection.commit()
        return render_template('buyer_checkout.html', product=product, cc_nums=cc_nums, mes="Order Placed")


@app.route('/buyer/info', methods=["GET" ,"POST"])
def buyers_info():
    return info("buyer")

@app.route('/buyer/orders', methods=['GET', 'POST'])
def buyer_order():
    connection = sql.connect('NM_database.db')
    if request.form['submit'] == "rating":
        seller = request.form['seller_sel']
        rating = request.form['rating']
        desc = request.form['desc']
        date = datetime.now().strftime("%m/%d/%Y")
        connection.execute(
            'INSERT INTO Ratings (Buyer_Email, Seller_Email, Date, Rating, Rating_Desc) VALUES (?,?,?,?,?);',(email, seller, date, rating, desc))
        connection.commit()
    if request.form['submit'] == "review":
        seller = request.form['seller_sel']
        product = request.form['item_sel']
        desc = request.form['desc']
        check =connection.execute('Select * FROM Reviews Where Seller_Email = ? AND Listing_ID =?',(seller, product)).fetchall()
        check = np.asarray(check)
        if check == []:
            connection.execute(
            'INSERT INTO Reviews (Buyer_Email, Seller_Email, Listing_ID, Review_Desc) VALUES (?,?,?,?);',
            (email,seller,product, desc))
        else:
            connection.execute('Update Reviews Set Review_Desc = ? Where Seller_Email = ? AND Listing_ID =?;', (desc, seller,product))
        connection.commit()

    orders = connection.execute('SELECT * FROM Orders WHERE buyer_email = ?;', [email]).fetchall()
    orders_temp = np.asarray(orders).flatten()
    ratings = connection.execute('SELECT * FROM ratings WHERE buyer_email = ?;', [email]).fetchall()
    reviews = connection.execute('SELECT * FROM reviews WHERE buyer_email = ?;', [email]).fetchall()
    sellers = connection.execute('SELECT Seller_Email FROM Orders WHERE buyer_email = ?;',
                                   [email]).fetchall()
    purchased = connection.execute('SELECT seller_email, Listing_id FROM Orders WHERE buyer_email = ?;',
                                   [email]).fetchall()
    purchased = json.dumps(purchased)

    return render_template('buyer_orders.html', orders=orders, ratings=ratings, reviews=reviews, sellers= sellers, purchased = purchased)

#Buyer functionaility
@app.route('/seller', methods=["GET", "POST"])
def sellers_page():
    connection = sql.connect('NM_database.db')
    is_buyer = connection.execute('SELECT email FROM Buyers WHERE email = ?;', [email]).fetchall()
    buyer = "false"
    if is_buyer!= []:
        buyer = "true"
    return render_template('seller_home.html', buyer = buyer)

@app.route('/seller/product_search', methods=["POST"])
def seller_product_search():
    return product_search("seller")

@app.route('/seller/info', methods=["GET" ,"POST"])
def seller_info():
    return info("seller")

@app.route('/seller/listing', methods=["GET" ,"POST"])
def seller_listing():
    connection = sql.connect('NM_database.db')
    listings = connection.execute('SELECT * FROM Product_Listing WHERE Seller_Email = ?;', [email]).fetchall()
    categories = connection.execute('Select Distinct category_name From Categories;').fetchall()
    categories = np.asarray(categories).flatten()
    if request.method == "GET":
        return render_template('seller_listing.html', listings = listings,categories =categories)  # for buyers
    if request.method == "POST":
        if request.form["submit"]== "create":
            L_ID= int(request.form["Listing_ID"])
            Category = request.form["Category"]
            Title = request.form["Title"]
            Name = request.form['Name']
            Desc = request.form["Desc"]
            Price = int(request.form["Price"])
            Quantity = int(request.form["Quantity"])
            if Price <0 or Quantity < 0:
                return render_template('seller_listing.html',listings =listings, mes ="Price and Quantity must be greater then or equal to 0", categories= categories)
            check = connection.execute('Select * FROM Product_Listing WHERE Listing_ID =? AND Seller_Email = ? collate NOCASE;', [L_ID, email]).fetchall()
            if check:
                return render_template('seller_listing.html',listings= listings, mes="Listing ID already exists", categories = categories)
            connection.execute('INSERT INTO Product_Listing (Seller_Email, Listing_ID, Category,Title, Product_Name,Product_Description, Price, Quantity) VALUES (?,?,?,?,?,?,?,?);', (email, L_ID, Category,Title,Name,Desc,Price,Quantity))
            connection.commit()
        if request.form["submit"] == "delete":
            L_ID = int(request.form["Listing_ID"])
            connection.execute('Update  Product_Listing Set product_active_period = "Not Active" WHERE Listing_ID =? AND Seller_Email = ?', (L_ID, email))
        listings = connection.execute('SELECT * FROM Product_Listing WHERE Seller_Email = ?;', [email]).fetchall()
        return render_template('seller_listing.html', listings =listings, categories= categories)
    return render_template('seller_listing.html', listings=listings, categories=categories)  # for buyers

#utility function
def product_search(user_type):
    if request.method == "POST":
        if request.form['submit'] == 'search':
          return populate_products(user_type, "Root")
        else:
         c = request.form['submit'];
         return populate_products(user_type,c)

def populate_products(user_type, cat):
    connection = sql.connect('NM_database.db')
    arr = fetch_under_cats(cat)
    query = "SELECT Listing_ID, Title, Price, Seller_Email, Listing_ID, Product_Name, Quantity, Product_Description FROM Product_Listing WHERE product_active_period = 'Active' AND Category Collate NOCASE IN (" + arr + ")Collate NOCASE AND Quantity > 0;"
    listings = connection.execute(query).fetchall()
    cats = connection.execute('SELECT parent_category, category_name FROM categories;').fetchall()
    cats = json.dumps(cats)
    return render_template('product_search.html', listings=listings, cats=cats, cat=cat, user=user_type)

def fetch_under_cats(cat):
    connection = sql.connect('NM_database.db')
    if cat=='Root':
        under_cats = connection.execute('SELECT DISTINCT Category FROM Product_Listing;').fetchall()
        under_cats = np.asarray(under_cats).flatten()
    else:
        under_cats = connection.execute('SELECT category_name FROM categories WHERE parent_category =?;', [cat]).fetchall()
        under_cats = np.asarray(under_cats).flatten()
        arr = under_cats
        under_cats = np.concatenate((under_cats, [cat]), axis=0)
        while arr != []:
            arr = "\",\"".join(arr)
            arr = "\"" + arr + "\""
            query = "SELECT category_name FROM categories WHERE parent_category COLLATE NOCASE IN ("+arr + ")Collate NOCASE;"
            arr = connection.execute(query).fetchall()
            arr = np.asarray(arr).flatten()
            under_cats = np.concatenate((arr, under_cats), axis = 0)
    under_cats = "\",\"".join(under_cats)
    under_cats = "\"" + under_cats + "\""
    return under_cats





def info(user_type):
    connection = sql.connect('NM_database.db')
    cc_nums = connection.execute('SELECT credit_card_num  FROM Credit_Cards WHERE Owner_email =?;',
                                 [email]).fetchall()
    if cc_nums:
        cc_l4 = cc_nums[0][0][3::-1]

    if user_type == "buyer":
        info = connection.execute('SELECT * FROM Buyers WHERE email = ?;', [email]).fetchall()
        h_a = connection.execute('SELECT * FROM Address WHERE address_id = ?;', [info[0][5]]).fetchall()
        h_a_zipinfo = connection.execute('SELECT city, state_id FROM Zipcode_Info WHERE zipcode= ?;', [h_a[0][1]]).fetchall()
        b_a = connection.execute('SELECT * FROM Address WHERE address_id = ?;', [info[0][6]]).fetchall()
        b_a_zipinfo = connection.execute('SELECT city, state_id FROM Zipcode_Info WHERE zipcode= ?;', [b_a[0][1]]).fetchall()
        if request.method == "GET":
            return render_template('info.html', user = user_type, cc_nums=cc_nums, info=info, h_a=h_a, b_a=b_a,
                                   cc_l4=cc_l4, h_a_zipinfo =h_a_zipinfo, b_a_zipinfo =b_a_zipinfo)  # for buyers
        if request.method == "POST":
            if request.form["submit"] == "password":
                new_ps = request.form['ps']
                connection.execute('UPDATE Users SET password = ? WHERE email =?;', [new_ps, email])
                ps = connection.execute('SELECT password FROM Users WHERE email = ?;', [email]).fetchall()
                connection.commit()
                return render_template('info.html', user = user_type, cc_nums=cc_nums, info=info, h_a=h_a, b_a=b_a, cc_l4=cc_l4,
                                       ps_mes="password reset")  # for buyers
    if user_type == "seller":
        if request.method == "POST":
            if request.form["submit"] == "password":
                new_ps = request.form['ps']
                connection.execute('UPDATE Users SET password = ? WHERE email =?;', [new_ps, email])
                ps = connection.execute('SELECT password FROM Users WHERE email = ?;', [email]).fetchall()
                connection.commit()
            return render_template('info.html', user = user_type, ps_mes = "password reset")
        return render_template('info.html', user=user_type)




if __name__ == '__main__':
    app.run()
