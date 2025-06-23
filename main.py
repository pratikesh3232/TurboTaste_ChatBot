from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import db_helper
import genric_helper



app = FastAPI()
# Dictionary to keep track of in-progress orders

# This will map session IDs to their respective orders
inprogress_orders = {}





@app.post("/")
async def handle_request(request: Request):
    payload = await request.json()
    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    output_contexts = payload['queryResult']['outputContexts']
    
    
    # Extract the session ID from the output contexts
    session_id = genric_helper.extract_session_id(output_contexts[0]["name"])   
    
    
    # Extract session ID from the output contexts
    intent_handler_dict = {
        'order.add - context: ongoing-order': add_to_order,
        # 'order.remove - context: ongoing-order': remove_from_order,
        # 'order.complete - context: ongoing-order': complete_order,
        'track.order - context: ongoing-tracking': track_order
    }
    #
    return intent_handler_dict[intent](parameters, session_id)








# # Function to save the order to the database
def add_to_order(Parameters:dict,session_id: str):
    food_item = Parameters['Food_item']
    quantity = Parameters['number1']


    if len(food_item) != len(quantity):
        fulfillment_text = "Sorry I didn't understand. Can you please specify food items and quantities clearly?"
    else:
        new_food_dict = dict(zip(food_item, quantity))


    if session_id not in inprogress_orders:
        inprogress_orders[session_id] = new_food_dict
    else:
        # If the session already exists, update the existing order
        current_food_dict = inprogress_orders[session_id]
        for key, value in new_food_dict.items():
            if key in current_food_dict:
                current_food_dict[key] += value
            else:
                current_food_dict[key] = value
        inprogress_orders[session_id] = current_food_dict



    order_str = genric_helper.get_str_from_food_dict(inprogress_orders[session_id])
    fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"


    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })
















## Function to track an order based on the order ID
def  track_order( parameters: dict):
    order_id =int(parameters['number'])

    # Fetch the order status from the database
    order_status = db_helper.get_order_status(order_id)
    # Prepare the response based on the order status
    fulfillment_text = ""

    if order_status:
        fulfillment_text = f"The order status for order id: {order_id} is: {order_status}"
    else:
        fulfillment_text = f"No order found with order id: {order_id}"
    
    # Return the response as JSON
    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })