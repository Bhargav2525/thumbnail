import json
import boto3
import os
from PIL import Image
from io import BytesIO
import datetime

s3_client = boto3.client('s3')
bucket_name = os.environ.get('bucket_name')
second_bucket_name = os.environ["second_bucket_name"]
dynamodb = boto3.resource('dynamodb')
table_name = 'thumbnail-app-MetaTable-UT3OEO35G2OF'
table = dynamodb.Table(table_name)
events = boto3.client('events')

# Handles Metadata of the image and inserts into DDB.
def metadata_handler(event, context):
    detail_data = event['detail']
    filename = detail_data['filename']
    Time = detail_data['Time']
    original_url = detail_data['original_url']
    thumbnail_url = detail_data['thumbnail_url']
    item = {"filename": filename ,"Time" : Time, "original_url": original_url , "thumbnail_url" : thumbnail_url}
    table.put_item(Item = item)
    return {}
    # while using step function
    # table.put_item(Item = event)
    # return {}

# Generates Thumbnail version of the image using PIL and inserts into S3.
def thumbnail_generator(event,context):
    print(event)
    try:
        file_name = event["Records"][0]['s3']['object']['key']
        file_insertion_time = event["Records"][0]["eventTime"]
        response = s3_client.get_object(Bucket=bucket_name, Key= file_name)
        image_data = response['Body'].read()
        image = Image.open(BytesIO(image_data))
        thumbnail_file_name = "thumbnail/" + file_name.split("/")[1]
        thumbnail_image = image.resize((100, 100))
        buffered_resized = BytesIO()
        thumbnail_image.save(buffered_resized, format="JPEG")  
        thumbnail_image_data = buffered_resized.getvalue()
        s3_client.put_object(
            Bucket=bucket_name,
            Key = thumbnail_file_name,
            Body = thumbnail_image_data,
            ContentType="image/jpeg"
        )
    except Exception as e:
        print(e)
        print("Exception in File Insertion Block")
        return {
            "StatusCode" : e.args[0],
            "headers" : {},
            "message" : e.args[1]
        }
    try:
        url1 = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket_name,
                'Key': file_name,
                'ResponseContentType': 'text/plain',
                'ResponseContentDisposition': 'attachment'
            },
            ExpiresIn=360000
        )
        url2 = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket_name ,
                'Key': thumbnail_file_name,
                'ResponseContentType': 'text/plain',
                'ResponseContentDisposition': 'attachment'
            },
            ExpiresIn=360000
        )
        print("url1:",url1,"url2:",url2)
    except Exception as e:
        print("Error in Generating Presigned URL")
    
    item = {"filename" : file_name.split("/")[1],"Time":str(file_insertion_time), "original_url": url1 ,"thumbnail_url": url2}
    response = events.put_events(
        Entries=[
            {
                'Time': datetime.datetime.now(),
                'Source': 'Lambda Publish',
                'Resources': [
                ],
                'DetailType': 'custom events',
                'Detail': json.dumps(item),
                'EventBusName': 'arn:aws:events:us-east-1:960351580303:event-bus/bhargav-test',
                'TraceHeader': 'string'
            },
        ],
    )
    print(response)
    return response
    # while using step function
    # try:
    #     print(event)
    #     file_name = event["detail"]['object']['key']
    #     file_insertion_time = event["time"]
    #     response = s3_client.get_object(Bucket=bucket_name, Key=file_name)
    #     image_data = response['Body'].read()
    #     image = Image.open(BytesIO(image_data))
    #     thumbnail_file_name = file_name + '_thumbnail.png'
    #     thumbnail_image = image.resize((100, 100))
    #     buffered_resized = BytesIO()
    #     thumbnail_image.save(buffered_resized, format="JPEG")  
    #     thumbnail_image_data = buffered_resized.getvalue()
    #     s3_client.put_object(
    #         Bucket=second_bucket_name,
    #         Key=thumbnail_file_name,
    #         Body=thumbnail_image_data,
    #         ContentType="image/jpeg" 
    #     )
    # except Exception as e:
    #     print("Exception in File Insertion Block")
    #     print(e)
    #     return {
    #         "StatusCode" : e.args[0],
    #         "headers" : {},
    #         "message" : e.args[1]
    #     }
    # try:
    #     url1 = s3_client.generate_presigned_url(
    #         ClientMethod='get_object',
    #         Params={
    #             'Bucket': bucket_name,
    #             'Key': file_name,
    #             'ResponseContentType': 'text/plain',
    #             'ResponseContentDisposition': 'attachment'
    #         },
    #         ExpiresIn=360000
    #     )
    #     url2 = s3_client.generate_presigned_url(
    #         ClientMethod='get_object',
    #         Params={
    #             'Bucket':second_bucket_name,
    #             'Key': thumbnail_file_name,
    #             'ResponseContentType': 'text/plain',
    #             'ResponseContentDisposition': 'attachment'
    #         },
    #         ExpiresIn=360000
    #     )
    #     print("url1:",url1,"url2:",url2)
    # except Exception as e:
    #     print("Error in Generating Presigned URL")
    
    # item = {"filename" : file_name,"Time":str(file_insertion_time), "original_url": url1 ,"thumbnail_url": url2}
    # return item
    

# Generates Presigned Post URL to upload files into S3.
def lambda_handler(event, context):
    bucket_name = os.environ.get("bucket_name", None)
    try:
        file_name = event.get("queryStringParameters").get("filename")
        response = s3_client.generate_presigned_post(
            Bucket=bucket_name,
            Key=file_name,
            Fields= {"Content-Type": "image/jpg"},
            ExpiresIn=3600,
        )
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(response),
        }
    except Exception as e:
        return {"statusCode": e.args[0], "body": json.dumps("Error in Exception block of Lambda handler")}
    
    return {"statusCode": 500, "body": json.dumps("Error processing the request!")}