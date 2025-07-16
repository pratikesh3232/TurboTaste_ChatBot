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
        'order_remove': remove_from_order,
        'Order_complete': complete_order,
        'Track_order Context:ongoing-order': track_order,
        'Cancel_Order': cancel_order
    }
    #
    return intent_handler_dict[intent](parameters, session_id)



def save_to_db(order: dict):
    next_order_id = db_helper.get_next_order_id()

    # Insert individual items along with quantity in orders table
    for food_item, quantity in order.items():
        rcode = db_helper.insert_order_item(
            food_item,
            quantity,
            next_order_id
        )

        if rcode == -1:
            return -1

    # Now insert order tracking status
    db_helper.insert_order_tracking(next_order_id, "in progress")

    return next_order_id



# Function to save the order to the database
# def add_to_order(Parameters:dict,session_id: str):
#     food_item = Parameters['Food_item']
#     quantity = Parameters['number1']


#     if len(food_item) != len(quantity):
#         fulfillment_text = "Sorry I didn't understand. Can you please specify food items and quantities clearly?"
#     else:
#         new_food_dict = dict(zip(food_item, quantity))


#     if session_id not in inprogress_orders:
#         inprogress_orders[session_id] = new_food_dict
#     else:
#         # If the session already exists, update the existing order
#         current_food_dict = inprogress_orders[session_id]
#         for key, value in new_food_dict.items():
#             if key in current_food_dict:
#                 current_food_dict[key] += value
#             else:
#                 current_food_dict[key] = value
#         inprogress_orders[session_id] = current_food_dict



#     order_str = genric_helper.get_str_from_food_dict(inprogress_orders[session_id])
#     fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"


#     return JSONResponse(content={
#         "fulfillmentText": fulfillment_text
#     })

def add_to_order(parameters: dict, session_id: str):
    Food_item    = parameters['Food_item']
    quantity = parameters['number1']
    # Check if the length of food items and quantities match
    # If they don't match, return an error message
    if len(Food_item) != len(quantity):
        fulfillment_text = "Sorry I didn't understand. Can you please specify food items and quantities clearly?"
    else:
        new_food_dict = dict(zip(Food_item, quantity))
        # If the session ID is not in in-progress orders, create a new order
        # If the session ID is already in in-progress orders, update the existing order
        if session_id in inprogress_orders:
            current_food_dict = inprogress_orders[session_id]
            current_food_dict.update(new_food_dict)
            inprogress_orders[session_id] = current_food_dict
        else:
            inprogress_orders[session_id] = new_food_dict
    # Generate a string representation of the current order
        order_str = genric_helper.get_str_from_food_dict(inprogress_orders[session_id])
        fulfillment_text = f"So far you have: {order_str}. Do you need anything else?"

    # return JSONResponse(content={
    #     "fulfillmentText": fulfillment_text
    # })

    return JSONResponse(content={
    "fulfillmentMessages": [
        {
            "payload": {
                "richContent": [
                    [
                        {
                            "type": "info",
                            "title": "🛒 Current Order",
                            "subtitle": fulfillment_text
                        },
                        {
                            "type": "chips",
                            "options": [
                                {"text": "Cancel Order"}
                            ]
                        }
                    ]
                ]
            }
        }
    ]
})


def complete_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentMessages": [
                {
                    "payload": {
                        "richContent": [
                            [
                                {
                                    "type": "info",
                                    "title": "⚠️ No Order Found",
                                    "subtitle": "I'm having trouble finding your order. Can you place a new one, please?"
                                },
                                {
                                    "type": "chips",
                                    "options": [
                                        {"text": "Start New Order"},
                                        {"text": "Help"}
                                    ]
                                }
                            ]
                        ]
                    }
                }
            ]
        })

    order = inprogress_orders[session_id]
    order_id = save_to_db(order)

    if order_id == -1:
        message = "❌ Sorry, we couldn’t process your order due to a backend error.\nPlease place a new order again."
        rich_response = [
            {
                "type": "info",
                "title": "Order Failed",
                "subtitle": message
            },
            {
                "type": "chips",
                "options": [
                    {"text": "Try Again"},
                    {"text": "Contact Support"}
                ]
            }
        ]
    else:
        order_total = db_helper.get_total_order_price(order_id)
        message = f"✅ Awesome! We have placed your order.\n\n🧾 Order ID: #{order_id}\n💰 Total: ${order_total}\n\nPlease pay at the time of delivery."
        rich_response = [
            {
                "type": "info",
                "title": "🎉 Order Confirmed",
                "subtitle": message
            },
            {
                "type": "chips",
                "options": [
                    {"text": "Track Order"},
                    {"text": "Exit"}
                ]
            }
        ]
        # Remove the order from session
        del inprogress_orders[session_id]

    return JSONResponse(content={
        "fulfillmentMessages": [
            {
                "payload": {
                    "richContent": [rich_response]
                }
            }
        ]
    })




# Function to track an order based on the order ID
def  track_order( parameters: dict,session_id: str):
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
    "fulfillmentMessages": [
        {
            "payload": {
                "richContent": [
                    [
                        {
                            "type": "info",
                            "title": "📦 Track Your Order",
                            "subtitle":f"The order status for order id: {order_id} is: {order_status}"
                        },
                        {
                            "type": "chips",
                            "options": [
                                { "text": "Start New Order" },
                                { "text": "Exit" }
                            ]
                        }
                    ]
                ]
            }
        }
    ]
})




def remove_from_order(parameters: dict, session_id: str):
    # Check if the session ID exists in in-progress orders
    # If it does not exist, return an error message
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": "I'm having a trouble finding your order. Sorry! Can you place a new order please?"
        })
    
    food_items = parameters["Food_item"]
    # Get the current order for the session ID
    current_order = inprogress_orders[session_id]

    removed_items = []
    no_such_items = []
    # Iterate through the food items to be removed
    # If an item is not in the current order, add it to no_such_items
    # If an item is in the current order, remove it and add it to removed_items


    for item in food_items:
        if item not in current_order:
            no_such_items.append(item)
        else:
            removed_items.append(item)
            del current_order[item]

    # Prepare the fulfillment text based on the removed and no-such items
    if len(removed_items) > 0:
        fulfillment_text = f'Removed {",".join(removed_items)} from your order!'

    if len(no_such_items) > 0:
        fulfillment_text = f' Your current order does not have {",".join(no_such_items)}'
    # If there are no items left in the current order, append a message indicating that the order is empty
    # If there are still items left in the current order, generate a string representation of the
    if len(current_order.keys()) == 0:
        fulfillment_text += " Your order is empty!"
    else:
        # If there are still items left in the order, generate a string representation of the current order
        # and append it to the fulfillment text
        order_str = genric_helper.get_str_from_food_dict(current_order)
        fulfillment_text += f" Here is what is left in your order: {order_str}"

    # Update the in-progress orders with the modified current order
    inprogress_orders[session_id] = current_order
    # continue the conversation by asking if the user needs anything else
    fulfillment_text += " Do you need anything else?"


# Return confirmation message with chips (buttons)
    return JSONResponse(content={
        "fulfillmentMessages": [
            {
                "payload": {
                    "richContent": [
                        [
                            {
                                "type": "info",
                                "title": "Removed Items",
                                "subtitle": fulfillment_text
                            },
                            {
                                "type": "chips",
                                "options": [
                                    { "text": "Start New Order" },
                                    { "text": "Exit" }
                                ]
                            }
                        ]
                    ]
                }
            }
        ]
    })






def cancel_order(parameters: dict,session_id: str):
    # Check if the session ID exists in in-progress orders
    if session_id not in inprogress_orders:
        return JSONResponse(content={
        "fulfillmentMessages": [
            {
                "payload": {
                    "richContent": [
                        [
                            {
                                "type": "info",
                                "title": "❌ Cant Find Order",
                                "subtitle": "I'm having trouble finding your order. Sorry! Can you place a new order instead?"
                            },
                            {
                                "type": "chips",
                                "options": [
                                    { "text": "Start New Order" }
                
                                ]
                            }
                        ]
                    ]
                }
            }
        ]
    })

        # return JSONResponse(content={
        #     "fulfillmentText": "I'm having trouble finding your order. Sorry! Can you place a new order instead?"
        # })

    # Delete the entire order for the session
    del inprogress_orders[session_id]

    # Return confirmation message with chips (buttons)
    return JSONResponse(content={
        "fulfillmentMessages": [
            {
                "payload": {
                    "richContent": [
                        [
                            {
                                "type": "info",
                                "title": "❌ Order Cancelled",
                                "subtitle": "Your entire order has been cancelled. Let me know if you’d like to start a new one."
                            },
                            {
                                "type": "chips",
                                "options": [
                                    { "text": "Start New Order" },
                                    { "text": "Exit" }
                                ]
                            }
                        ]
                    ]
                }
            }
        ]
    })
