from datetime import date

import httplib2
import apiclient
from oauth2client.service_account import ServiceAccountCredentials
from sqlalchemy import text

from sqlalchemy.ext.asyncio import AsyncSession

from data.config import CREDENTIALS_FILE, SPREADSHEET_ID
from db.models import Order

credentials = ServiceAccountCredentials.from_json_keyfile_name(
    CREDENTIALS_FILE,
    ['https://www.googleapis.com/auth/spreadsheets',
     'https://www.googleapis.com/auth/drive'])
httpAuth = credentials.authorize(httplib2.Http())
service = apiclient.discovery.build('sheets', 'v4', http=httpAuth)


async def row_record(order: Order, date: date, session: AsyncSession):
    query = f"select p.name, cp.quantity from 'cart_product' cp " \
            f"left join 'product' p on p.id = cp.product_id WHERE cp.cart_id = {order.cart_id}"
    values_article = ''
    values_quantity = ''
    for name, quantity in await session.execute(text(query)):
        values_article += name + '\n'
        values_quantity += str(quantity) + '\n'
    return service.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"A{order.id + 1}:J{order.id + 1}",
                 "majorDimension": "ROWS",
                 "values": [[
                     str(order.id),  # ID замовлення
                     date.strftime("%d.%m.%Y"),  # Дата
                     values_article,  # Товар
                     values_quantity,  # Кількість
                     str(int(order.total_amount / 100)),  # Загальна сума
                     order.full_name,  # Повне ім'я
                     order.phone_number,  # Номер телефону
                     order.region,  # Область
                     order.city,  # Місто
                     order.nova_poshta_number  # Відділення НП
                 ]]}
            ]
        }
    ).execute()
