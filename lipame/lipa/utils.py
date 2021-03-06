import base64
import datetime
import json

from django.conf import settings
import requests
import uuid
import boto3


def send_sms(phone_number, message, sender_id):
    """ A task to send messages to users using Amazon SNS asynchronously.
    """
    sns = boto3.client(
        'sns',
        region_name=settings.AWS_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )
    sns.publish(
        PhoneNumber=str(phone_number),
        Message=message,
        MessageAttributes={
            'AWS.SNS.SMS.SenderID': {
                'DataType': 'String',
                'StringValue': (sender_id if sender_id else settings.AMAZON_SNS_SENDER_ID)
            },
            'AWS.SNS.SMS.SMSType': {
                'DataType': 'String',
                'StringValue': 'Transactional'
            }
        }
    )


def make_request(url, data, request_date, msisdn, pin):
    x_correlation_id = str(uuid.uuid1())  # TODO
    result = msisdn + ":" + pin
    auth_key = base64.b64encode(result.encode('ascii'))
    header = {
            'Content-Type': 'application/json',
            'X-CorrelationID': x_correlation_id,
            'Date': request_date,
            'Authorization': auth_key
    }

    return requests.post(url, data=json.dumps(data), headers=header)


def do_merchant_payment(msisdn, amount, pin="1357"):
    request_date = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    data = {"amount": str(amount),
            "currency": settings.CURRENCY_CODE,
            "type": "merchantpayment",
            "requestDate": request_date,
            "debitParty": [
                {
                    "key": "FROM",
                    "value": msisdn
                }
            ],
            "creditParty": [
                {
                    "key": "TO",
                    "value": settings.MERCHANT_ID
                }
            ]}

    return make_request(settings.TRANSACTIONS_URL, data, request_date, msisdn, pin)


def do_wallet_topup(msisdn, amount, pin="1357"):
    request_date = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    data = {
        "amount": str(amount),
        "currency": settings.CURRENCY_CODE,
        "type": "transfer",
        "requestDate": request_date,
        "creditParty": [
            {
                "key": "TO",
                "value": msisdn
            }
        ]}
    return make_request(settings.TRANSACTIONS_URL, data, request_date, msisdn, pin)


def get_balance(msisdn, account_type='customer', pin="1357"):
    auth_key = base64.b64encode(msisdn + ":" + pin)
    header = {
            'X-User-Credential-2': pin,
            'Authorization': auth_key,
            'X-Account-Type': account_type
    }
    balance_url = settings.BALANCE_URL + '/' + msisdn + '/balance'
    return requests.get(balance_url, headers=header)


def get_transactions(msisdn, pin="1357"):
    request_date = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    return make_request(settings.TRANSACTIONS_URL, None, request_date, msisdn, pin)


def get_transaction(transaction_id, msisdn, pin="1357"):
    auth_key = base64.b64encode(msisdn + ":" + pin)
    request_date = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
    header = {
            'Authorization': auth_key,
            'Date': request_date
    }
    balance_url = settings.TRANSACTIONS_URL + transaction_id
    return requests.post(balance_url, headers=header)
