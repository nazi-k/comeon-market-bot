from datetime import datetime, timedelta

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


async def row_record(order: Order, date_time: datetime, session: AsyncSession):
    query = "select (p.name || ' ' || rez.modifications) as product_modification_name, rez.quantity " \
            "from (select MAX(pm.product_id) as product_id, " \
            "      array_to_string(ARRAY_AGG(m.value), ' ') as modifications, " \
            "      MAX(cpm.quantity) as quantity, MAX(pm.price) as price " \
            "      from product_modification pm " \
            "      left join modification m on pm.id = m.product_modification_id " \
            "      left join cart_product_modification cpm on pm.id = cpm.product_modification_id " \
            f"     where cpm.cart_id = {order.cart_id} " \
            "      group by m.product_modification_id) rez " \
            "left join product p on rez.product_id = p.id"
    date_time += timedelta(hours=3)
    values_article = ''
    values_quantity = ''
    for product_modification_name, quantity in await session.execute(text(query)):
        values_article += product_modification_name + '\n'
        values_quantity += str(quantity) + '\n'
    else:
        values_article = values_article[:-1]
        values_quantity = values_quantity[:-1]
    return service.spreadsheets().values().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": f"A{order.id + 1}:K{order.id + 1}",
                 "majorDimension": "ROWS",
                 "values": [[
                     str(order.id),                          # ID замовлення
                     date_time.date().strftime("%d.%m.%Y"),  # Дата
                     date_time.time().strftime("%H:%M:%S"),  # Час
                     values_article,                         # Товар
                     values_quantity,                        # Кількість
                     str(order.total_amount),                # Загальна сума
                     order.full_name,                        # Повне ім'я
                     order.phone_number,                     # Номер телефону
                     order.region,                           # Область
                     order.city,                             # Місто
                     order.nova_poshta_number                # Відділення НП
                 ]]}
            ]
        }
    ).execute()
