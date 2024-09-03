from flask import Flask, request, jsonify
import json
from urllib.parse import quote, urlparse
import requests
from selectolax.parser import HTMLParser
import logging

app = Flask(__name__)

def get_base64_str(source_url):
    try:
        url = urlparse(source_url)
        path = url.path.split("/")
        if (
            url.hostname == "news.google.com"
            and len(path) > 1
            and path[-2] in ["articles", "read"]
        ):
            base64_str = path[-1]
            return {"status": True, "base64_str": base64_str}
        else:
            return {"status": False, "message": "Invalid Google News URL format."}
    except Exception as e:
        logging.error(f"get_base64_str error: {str(e)}")
        return {"status": False, "message": f"Error in get_base64_str: {str(e)}"}


def get_decoding_params(base64_str):
    try:

        response = requests.get(f"https://news.google.com/articles/{base64_str}")
        response.raise_for_status()

        parser = HTMLParser(response.text)
        datas = parser.css_first("c-wiz > div[jscontroller]")
        if datas is None:
            return {
                "status": False,
                "message": "Failed to fetch data attributes from Google News.",
            }

        return {
            "status": True,
            "signature": datas.attributes.get("data-n-a-sg"),
            "timestamp": datas.attributes.get("data-n-a-ts"),
            "base64_str": base64_str,
        }
    except requests.exceptions.RequestException as req_err:
        logging.error(f"get_decoding_params Request error: {str(req_err)}")
        return {
            "status": False,
            "message": f"Request error in get_decoding_params: {str(req_err)}",
        }
    except Exception as e:
        logging.error(f"get_decoding_params error: {str(e)}")
        return {"status": False, "message": f"Error in get_decoding_params: {str(e)}"}


def decode_url(signature, timestamp, base64_str):
    try:
        url = "https://news.google.com/_/DotsSplashUi/data/batchexecute"

        payload = [
            "Fbv4je",
            f'["garturlreq",[["X","X",["X","X"],null,null,1,1,"US:en",null,1,null,null,null,null,null,0,1],"X","X",1,[1,1,1],1,1,null,0,0,null,0],"{base64_str}",{timestamp},"{signature}"]',
        ]
        headers = {
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        }
        response = requests.post(
            url, headers=headers, data=f"f.req={quote(json.dumps([[payload]]))}"
        )
        response.raise_for_status()

        parsed_data = json.loads(response.text.split("\n\n")[1])[:-2]
        decoded_url = json.loads(parsed_data[0][2])[1]

        return {"status": True, "decoded_url": decoded_url}
    except requests.exceptions.RequestException as req_err:
        logging.error(f"decode_url Request error: {str(req_err)}")
        return {
            "status": False,
            "message": f"Request error in decode_url: {str(req_err)}",
        }
    except (json.JSONDecodeError, IndexError, TypeError) as parse_err:
        logging.error(f"decode_url Parsing error: {str(parse_err)}")
        return {
            "status": False,
            "message": f"Parsing error in decode_url: {str(parse_err)}",
        }
    except Exception as e:
        logging.error(f"decode_url error: {str(e)}")
        return {"status": False, "message": f"Error in decode_url: {str(e)}"}
def decode_google_news_url(source_url, interval=1):
    try:
        base64_str_response = get_base64_str(source_url)
        if not base64_str_response["status"]:
            return base64_str_response

        decoding_params_response = get_decoding_params(base64_str_response["base64_str"])
        if not decoding_params_response["status"]:
            return decoding_params_response

        signature = decoding_params_response["signature"]
        timestamp = decoding_params_response["timestamp"]
        base64_str = decoding_params_response["base64_str"]

        decoded_url_response = decode_url(signature, timestamp, base64_str)
        if not decoded_url_response["status"]:
            return decoded_url_response

        return {"status": True, "decoded_url": decoded_url_response["decoded_url"]}
    except Exception as e:
        logging.error(f"decode_google_news_url error: {str(e)}")
        return {"status": False, "message": f"Error in decode_google_news_url: {str(e)}"}

@app.route('/decode_url', methods=['POST'])
def decode_url_endpoint():
    data = request.json
    source_url = data.get('source_url')
    if not source_url:
        return jsonify({"status": False, "message": "No source_url provided"}), 400

    result = decode_google_news_url(source_url)
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
