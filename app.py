from flask import Flask, request, render_template
from flask_mysqldb import MySQL
from flask_cors import CORS
from flask import jsonify
from datetime import datetime

app = Flask(__name__)
CORS(app)
 
app.config['MYSQL_HOST'] = '192.168.1.3'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'aezakmi143'
app.config['MYSQL_DB'] = 'minimart'
 
mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search-products')
def search_products():
    args = request.args
    search = args.get('search')
    product_desc = ''

    # print(search, product_desc)

    if search.isalpha() or (' ' in search):
        product_desc = f"'%{search}%'"
        search = "''"
    else:
        search = f"'%{search}%'"
        product_desc = "''"

    query = f"""SELECT product_code as 'Product Code', product_desc as 'Description', 
                FORMAT((((SELECT IFNULL(SUM(delivery_quantity), 0) 
                FROM deliveries WHERE deliveries.delivery_product = products.id LIMIT 1) - (SELECT IFNULL(SUM(quantity), 0) 
                    FROM trash WHERE trash.product_id = products.id LIMIT 1)) - (SELECT IFNULL(SUM(quantity), 0) 
                        FROM solditem WHERE solditem.prodict_id = products.id AND (SELECT isVoid 
                            FROM sales WHERE sales.id = solditem.sales_id LIMIT 1) = 0  LIMIT 1)), 2) as 'Stock', 
                            FORMAT(product_reorder, 2) as 'Re-Order', IF((((SELECT IFNULL(SUM(delivery_quantity), 0) 
                            FROM deliveries WHERE deliveries.delivery_product = products.id LIMIT 1) - (SELECT IFNULL(SUM(quantity), 0) 
                                FROM trash WHERE trash.product_id = products.id LIMIT 1)) - (SELECT IFNULL(SUM(quantity), 0) 
                                    FROM solditem WHERE solditem.prodict_id = products.id AND (SELECT isVoid FROM sales WHERE sales.id = solditem.sales_id LIMIT 1) = 0  LIMIT 1)) <= product_reorder, 
                                    'Critical Level Stocks', '-') as 'Status', product_price, product_ws_price FROM products WHERE product_code LIKE {search} OR product_desc LIKE {product_desc} ORDER BY product_desc ASC;"""

    # print(query)
    cursor = mysql.connection.cursor()
    cursor.execute(query)

    data = cursor.fetchall()

    mysql.connection.commit()
    cursor.close()

    prod_array = []
    index = 0
    for product in data:
        prod_array.append({
            "product_code": product[0],
            "product_desc": product[1],
            "stock": product[2],
            "reorderStock": product[3],
            "product_status": product[4],
            "product_price": product[5],
            "product_ws_price": product[6]
        })
        # index += 1

    return jsonify({'products': prod_array})

@app.route('/add-stock', methods=['POST'])
def add_stock():
    if request.method == 'POST':
        cursor = mysql.connection.cursor()

        delivery_id_query = f"select delivery_id from deliveries order by id desc limit 1;"
        cursor.execute(delivery_id_query)
        delivery_id_query_res = cursor.fetchall()[0]

        if delivery_id_query_res[0]:
            delivery_id = delivery_id_query_res[0]
        
        else:
            delivery_id = 0

        delivery_id_number = int(delivery_id[1:]) + 1
        delivery_ID = "D{:07d}".format(delivery_id_number)

        product_code = request.json.get('product_code')
        product_quantity = float(request.json.get('stock'))
        remarks = request.json.get('remarks')
        delivery_date = datetime.now().date()
        delivered_by = request.json.get('delivered_by')
        
        query = f"""INSERT INTO `deliveries` (`delivery_id`, `delivery_product`, `delivery_quantity`, `delivery_remarks`, `delivery_date`, `delivered_by`) 
                    VALUES ('{delivery_ID}', 
                    (SELECT products.id FROM products WHERE product_code = '{product_code}' LIMIT 1), {product_quantity}, '{remarks}', '{delivery_date}', '{delivered_by}');"""

        cursor.execute(query)
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({"message": "Stock Added Successfully"})

@app.route('/trash-stock', methods=['POST'])
def trash_stock():
    if request.method == 'POST':
        cursor = mysql.connection.cursor()

        trash_id_query = f"select trash_code from trash order by id desc limit 1;"
        cursor.execute(trash_id_query)
        trash_id_query_res = cursor.fetchall()[0]

        if trash_id_query_res[0]:
            trash_id = trash_id_query_res[0]
        
        else:
            trash_id = 0

        trash_id_number = int(trash_id[3:]) + 1
        trash_ID = "D{:07d}".format(trash_id_number)

        product_code = request.json.get('product_code')
        product_quantity = float(request.json.get('stock_to_trash'))
        remarks = request.json.get('remarks')
        trash_date = datetime.now().date()
        
        query = f"""INSERT INTO `trash` (`trash_code`, `product_id`, `quantity`, `reason`, `date_trashed`) 
                     VALUES ('{trash_ID}', (SELECT products.id FROM products WHERE product_code = '{product_code}' LIMIT 1), {product_quantity}, '{remarks}', '{trash_date}');"""

        cursor.execute(query)
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({"message": "Stock Removed Successfully"})


@app.route('/add-product', methods=['POST'])
def add_product():
    if request.method == 'POST':
        cursor = mysql.connection.cursor()

        product_code = request.json.get('product_code')
        product_desc = request.json.get('description')
        product_unit = request.json.get('unit')
        product_price = request.json.get('retail_price')
        product_ws_price = request.json.get('wholesale_price')
        product_reorder = request.json.get('reorderStock')
        product_category = request.json.get('product_category')
        has_pack = request.json.get('has_pack')
        pack_price = request.json.get('pack_price')
        pack_qty = request.json.get('pack_quantity')

        query = f"""INSERT INTO `products` (`product_code`, `product_desc`, `product_unit`, `product_price`, `product_ws_price`, `product_reorder`, 
                    `product_category`, `has_pack`, `pack_price`, `pack_qty`) 
                    VALUES ('{product_code}', '{product_desc}', '{product_unit}', {product_price}, {product_ws_price}, {product_reorder}, 
                    (SELECT id FROM product_category WHERE category_name = '{product_category}' LIMIT 1), {has_pack}, {pack_price}, {pack_qty});"""

        try:
            cursor.execute(query)
            mysql.connection.commit()
            cursor.close()
            return jsonify({"message": "Product Added Successfully"})
             
        except Exception as e:
            print(e)
            print(query)
            return jsonify({"message": e}), 500
