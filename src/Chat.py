class Chat:
    sheetId = -1,
    chatId = -1,
    tableName="none"
    def __init__(self, s, c ,t):
        self.sheetId = s
        self.chatId = c
        self.tableName = t
        print("Created chat object with SHEETID: "+s+" CHATID: "+c+" TABLE NAME: "+t)

