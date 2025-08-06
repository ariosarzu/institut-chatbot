from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    # Bu yerda chatbot mantiqi bo'ladi
    user_message = data['message']
    bot_response = f"Sizning xabaringiz: {user_message}"
    return jsonify({'response': bot_response})

if __name__ == '__main__':
    app.run(debug=True)
