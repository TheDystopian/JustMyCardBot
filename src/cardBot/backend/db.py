from weakref import finalize
from shutil import rmtree
import psycopg
from psycopg import DatabaseError, sql
from json import dumps
from collections.abc import Iterable


class DB:
    def __init__(self, config):
        self.__DB = psycopg.connect(
            dbname=config["dbname"],
            user=config["user"],
            password=config["passwd"],
            host=config["host"],
            port=config["port"],
        )
        self.__DB.autocommit = True
        self.__DBCursor = self.__DB.cursor()
        self.__DBCursor.execute("select * from userdata LIMIT 0")
        self.__DBColumns = [row[0] for row in self.__DBCursor.description]
        self.__final = finalize(self, rmtree, self.__DBCursor, self.__DB)
        

    def __composeDictionary(self, data: list|tuple, *, columns = None):
        if columns is None: columns = self.__DBColumns
        return dict(zip(columns, data)) if data else None

    def add(self, value, *, column = 'id'):
        try: 
            self.__DBCursor.execute(sql.SQL(f"INSERT INTO userdata ({sql.Identifier(column).as_string(self.__DBCursor)}) VALUES (%s)"), (value,))
        except DatabaseError:
            self.__DB.rollback()

    def get(self, user = None, *, filterCol: str = 'id', columns: str|list = None):
        try:
            data = list(map(
                self.__composeDictionary,
                self.__DBCursor.execute(
                sql.SQL(
                    'select {} from userdata{}'.format(
                        '*' if not columns else sql.SQL(',').join(list(map(sql.Identifier, columns if isinstance(columns, Iterable) else [columns]))),
                        f' where {sql.Identifier(filterCol).as_string(self.__DBCursor)} = %s' if filterCol and user else ''
                    )
                ),
                (user,) if filterCol and user else ()
            ).fetchall()))
            
            return data[-1] if user and data else data
        except DatabaseError:
            self.__DB.rollback()

    def edit(self, data: dict, *, column: str = 'id'):
        find = {column: data[column]}
        
        data = {
            key: (
                dumps(val) 
                if (
                    isinstance(val, dict)
                    or (isinstance(val, Iterable) and True in [isinstance(a, dict) for a in val])
                )
                else val
            )
            for key, val in data.items()
            if key != column
        }
        
        try:
            self.__DBCursor.execute(
               sql.SQL(
                   'update userdata set {} where {} = {}'.format(
                        sql.SQL(', ').join([
                            sql.SQL('{} = {}').format(
                                sql.Identifier(key),
                                sql.Placeholder(key)
                            )
                            for key in data.keys()
                        ]).as_string(self.__DBCursor),
                        sql.Identifier(column).as_string(self.__DBCursor),
                        sql.Placeholder(column).as_string(self.__DBCursor)
                    )
                ),
               data | find
            )  
        except DatabaseError:
            self.__DB.rollback()
            
    def __exit__(self):
        self.__DBCursor.close()
        self.__DB.close()