# 发送文本消息

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /api/send_text_msg:
    post:
      summary: 发送文本消息
      deprecated: false
      description: ''
      tags: []
      parameters: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                wxid:
                  type: string
                msg:
                  type: string
              x-apifox-orders:
                - wxid
                - msg
              required:
                - wxid
                - msg
            example:
              wxid: filehelper
              msg: '6666666666'
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
          headers: {}
          x-apifox-name: 成功
      security: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/8029877/apis/api-436529184-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: ''
    description: 开发环境
security: []

```

# 发送AT消息

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /api/send_at_text:
    post:
      summary: 发送AT消息
      deprecated: false
      description: ''
      tags: []
      parameters: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                roomId:
                  type: string
                msg:
                  type: string
                wxids:
                  type: string
              x-apifox-orders:
                - roomId
                - msg
                - wxids
              required:
                - roomId
                - msg
                - wxids
            example:
              wxids: wxid_ozyqateb85un22,wxid_smntff8632e122
              msg:  @测测666  @哈哈哈哈哈哈 测试
              roomId: 49767299448@chatroom
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
          headers: {}
          x-apifox-name: 成功
      security: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/8029877/apis/api-436530464-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: ''
    description: 开发环境
security: []

```

# 发送拍一拍

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /api/send_pat:
    post:
      summary: 发送拍一拍
      deprecated: false
      description: ''
      tags: []
      parameters: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                roomId:
                  type: string
                wxid:
                  type: string
              x-apifox-orders:
                - roomId
                - wxid
              required:
                - roomId
                - wxid
            example:
              roomId: wxid_hv8oepkfkkml12
              wxid: wxid_hv8oepkfkkml12
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
          headers: {}
          x-apifox-name: 成功
      security: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/8029877/apis/api-436531417-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: ''
    description: 开发环境
security: []

```

# 发送引用消息

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /api/send_quote:
    post:
      summary: 发送引用消息
      deprecated: false
      description: ''
      tags: []
      parameters: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                reply:
                  type: string
                referContent:
                  type: string
                fromUsr:
                  type: string
                newmsgid:
                  type: string
                msgSource:
                  type: string
                createTime:
                  type: integer
                sendto:
                  type: string
              x-apifox-orders:
                - reply
                - referContent
                - fromUsr
                - newmsgid
                - msgSource
                - createTime
                - sendto
              required:
                - reply
                - referContent
                - fromUsr
                - newmsgid
                - msgSource
                - createTime
                - sendto
            example:
              reply: 你好
              referContent: 你好
              fromUsr: wxid_ozyqateb85un22
              newmsgid: '5217518642639526576'
              msgSource: 这个参数可要可不要
              createTime: 0
              sendto: 49767299448@chatroom
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
          headers: {}
          x-apifox-name: 成功
      security: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/8029877/apis/api-436531460-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: ''
    description: 开发环境
security: []

```

# 个人发送文本消息回调

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /个人发送文本消息回调:
    put:
      summary: 个人发送文本消息回调
      deprecated: false
      description: ''
      tags: []
      parameters: []
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
          headers: {}
          x-apifox-name: 成功
      security: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/8029877/apis/api-436532407-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: ''
    description: 开发环境
security: []

```

# 语音转文本

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /api/get_voice_trans:
    post:
      summary: 语音转文本
      deprecated: false
      description: ''
      tags: []
      parameters: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                clientMsgId:
                  type: string
                newMsgId:
                  type: string
                length:
                  type: string
              x-apifox-orders:
                - clientMsgId
                - newMsgId
                - length
              required:
                - clientMsgId
                - newMsgId
                - length
            example:
              clientMsgId: '8111825985001399988'
              newMsgId: 211095990
              length: 11832
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
          headers: {}
          x-apifox-name: 成功
      security: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/8029877/apis/api-436534604-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: ''
    description: 开发环境
security: []

```

# 查询群成员信息

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /api/get_group_member_contact:
    post:
      summary: 查询群成员信息
      deprecated: false
      description: ''
      tags: []
      parameters: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                wxid:
                  type: string
                roomId:
                  type: string
              x-apifox-orders:
                - wxid
                - roomId
              required:
                - wxid
                - roomId
            example:
              wxid: wxid_8zggbw1yo5ib22
              roomId: 18402658081@chatroom
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
              example:
                baseResponse:
                  ret: 0
                  errMsg: {}
                contactCount: 1
                contactList:
                  - userName:
                      String: 群成员的wxid
                    nickName:
                      String: 不必
                    pyinitial:
                      String: BB
                    quanPin:
                      String: bubi
                    sex: 1
                    imgBuf:
                      iLen: 0
                    bitMask: 4294967295
                    bitVal: 3
                    imgFlag: 3
                    remark:
                      String: '9763'
                    remarkPyinitial:
                      String: '9763'
                    remarkQuanPin:
                      String: '9763'
                    contactType: 0
                    roomInfoCount: 0
                    domainList: {}
                    chatRoomNotify: 0
                    addContactScene: 0
                    province: Zhejiang
                    city: Hangzhou
                    signature: 特别害怕失去很熟悉的人
                    personalCard: 1
                    hasWeiXinHdHeadImg: 1
                    verifyFlag: 0
                    level: 0
                    source: 3
                    alias: jryswygq
                    weiboFlag: 0
                    albumStyle: 0
                    albumFlag: 0
                    snsUserInfo:
                      snsFlag: 1
                      snsBgimgId: >-
                        http://shmmsns.qpic.cn/mmsns/qcKhiayu3sNlcQLCwMDHfX38h9o7pCHkLtgBam5F6IgeABvibBTTib1bXiaVjCPZzEYTtVsbvian0EIk/0
                      snsBgobjectId: '14693141287014765172'
                      snsFlagEx: 7297
                      snsPrivacyRecent: 72
                    country: CN
                    bigHeadImgUrl: >-
                      https://wx.qlogo.cn/mmhead/ver_1/hic1c1goZbfmqcPfk2UllbdDGA5TC4ZwB7uINxase77pCZX2OU2MicGBw1ia3jBHKLPnbcSoySrCfsul8DjQBwAAAyPTA5Th5yibtZNBuxZhR8KIWvRqTGXNEQgticdEF61SX/0
                    smallHeadImgUrl: >-
                      https://wx.qlogo.cn/mmhead/ver_1/hic1c1goZbfmqcPfk2UllbdDGA5TC4ZwB7uINxase77pCZX2OU2MicGBw1ia3jBHKLPnbcSoySrCfsul8DjQBwAAAyPTA5Th5yibtZNBuxZhR8KIWvRqTGXNEQgticdEF61SX/132
                    myBrandList: <brandlist></brandlist>
                    customizedInfo:
                      brandFlag: 0
                    headImgMd5: 00a7b20ff61ed9356a1221a6e265134d
                    encryptUserName: V3
                    additionalContactList:
                      linkedinContactItem: {}
                    chatroomVersion: 0
                    chatroomMaxCount: 0
                    chatroomAccessType: 0
                    newChatroomData:
                      memberCount: 0
                      infoMask: 0
                      chatRoomUserName:
                        String: 49767299448@chatroom
                      watchMemberCount: 0
                    deleteFlag: 0
                    phoneNumListInfo:
                      count: 0
                    chatroomInfoVersion: 0
                    deleteContactScene: 0
                    chatroomStatus: 0
                    extFlag: 0
                    chatRoomBusinessType: '0'
                    friendUserName: 群成员的wxid
                    textStatusFlag: 2
                    ringBackSetting:
                      finderObjectId: '0'
                      startTs: 0
                      endTs: 0
                    bitMask2: '18446744073709551615'
                    bitValue2: '256'
                    contactExtraInfoBuf:
                      iLen: 0
                    isInChatRoom: 0
                    eraseChatRoomMemberData: 0
                ret:
                  - 0
                verifyUserValidTicketList:
                  username: 群成员的wxid
                  antispamticket: V4
          headers: {}
          x-apifox-name: 成功
      security: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/8029877/apis/api-436617596-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: ''
    description: 开发环境
security: []

```

# 群聊消息回调

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /主动推送的群聊消息:
    put:
      summary: 群聊消息回调
      deprecated: false
      description: ''
      tags: []
      parameters: []
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
              example:
                content:
                  String: 原始消息内容（包含发送者 wxid + 冒号 + 实际消息内容）
                createTime: 消息创建时间（Unix 时间戳，秒）
                fromUserName:
                  String: 群聊 ID（@chatroom 结尾）
                imgBuf:
                  iLen: 图片数据长度（0 表示无图片）
                imgStatus: 图片状态（1=有图，0=无图）
                member_info:
                  addChatRoomSceneNewXml: 入群场景 XML（包含邀请人信息）
                  bigHeadImgUrl: 群成员头像大图 URL
                  chatroomMemberFlag: 群成员标志位（内部字段）
                  inviterUserName: 邀请者的 wxid
                  nickName: 群成员昵称
                  smallHeadImgUrl: 群成员头像小图 URL
                  status: 群成员状态（0=正常，1=禁言 等）
                  userName: 群成员的 wxid
                messageType: 消息类型描述（群聊消息 / 私聊消息）
                msgId: 消息 ID（本地整型值）
                msgSeq: 消息序列号
                msgSource: 消息源的 XML（包含群信息，如成员数、签名等）
                msgType: 消息类型数值（1=文本，3=图片，43=视频 等）
                newMsgId: 消息唯一 ID（服务器下发，字符串类型）
                pushContent: 推送文案（昵称 + 消息内容，用于通知栏展示）
                real_content: 实际消息内容（去掉 wxid 和换行符之后的文本）
                sender_nick: 发送者昵称（可能为空）
                status: 消息状态（3=已送达 等）
                toUserName:
                  String: 消息接收方 wxid（通常是自己）
          headers: {}
          x-apifox-name: 成功
      security: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/8029877/apis/api-436644785-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: ''
    description: 开发环境
security: []

```

# 私聊消息回调

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /主动推送的私聊消息:
    put:
      summary: 私聊消息回调
      deprecated: false
      description: ''
      tags: []
      parameters: []
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
              example:
                content:
                  String: 消息内容（文本）
                createTime: 消息创建时间（Unix 时间戳，秒）
                from: 来自登录的哪个wxid
                fromUserName:
                  String: 发送者账号（wxid 或群号@chatroom）
                http_port: HTTP 服务端口（调试用）
                imgBuf:
                  iLen: 图片数据长度（为 0 表示无图片）
                imgStatus: 图片状态（1=有图，0=无图）
                messageType: 消息类型描述（如 私聊消息 / 群聊消息）
                msgId: 消息 ID（本地生成的整型值）
                msgSeq: 消息序列号
                msgSource: 消息源的 XML 描述（包含群成员数/签名等）
                msgType: 消息类型数值（1=文本，3=图片，43=视频 等）
                newMsgId: 消息唯一 ID（服务器下发，字符串类型）
                pid: 进程 ID（调试信息）
                pushContent: 推送内容（带有发送者昵称 + 消息预览）
                sender_nick: 发送者昵称（可能为空）
                sender_profile:
                  alias: 用户别名
                  bigHeadImgUrl: 用户头像大图 URL
                  bitMask: 标志位（内部用途）
                  bitVal: 标志值（内部用途）
                  city: 用户所在城市
                  country: 用户所在国家
                  description: 个性签名
                  encryptUserName: 加密后的用户名
                  hasWeiXinHdHeadImg: 是否有高清头像（1=有，0=无）
                  imgBuf:
                    buffer: 头像 buffer（一般为空）
                    iLen: 头像 buffer 长度
                  imgFlag: 头像标志
                  labelIdlist: 标签 ID 列表
                  nickName:
                    String: 用户昵称
                  phoneNumListInfo:
                    count: 绑定的手机号数量
                  province: 省份
                  pyinitial:
                    String: 昵称拼音首字母
                  quanPin:
                    String: 昵称全拼
                  remark:
                    String: 备注名
                  remarkPyinitial:
                    String: 备注名拼音首字母
                  remarkQuanPin:
                    String: 备注名全拼
                  sex: 性别（1=男，2=女，0=未知）
                  smallHeadImgUrl: 用户头像小图 URL
                  snsUserInfo:
                    snsFlag: 朋友圈标志位（1=可见）
                  textStatusFlag: 状态标志（内部用途）
                  userName:
                    String: 用户的 wxid
                  verifyFlag: 认证标志（大 V 等）
                status: 消息状态（3=已送达 等）
                toUserName:
                  String: 接收者 wxid（通常是自己）
          headers: {}
          x-apifox-name: 成功
      security: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/8029877/apis/api-436645190-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: ''
    description: 开发环境
security: []

```

# 批量发送消息

## OpenAPI Specification

```yaml
openapi: 3.0.1
info:
  title: ''
  description: ''
  version: 1.0.0
paths:
  /api/batch_send_text_msg:
    post:
      summary: 批量发送消息
      deprecated: false
      description: ''
      tags: []
      parameters: []
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties: {}
            example:
              messages:
                - wxid: filehelper
                  msg: 消息1
                - wxid: filehelper
                  msg: 消息2
                - wxid: filehelper
                  msg: 消息3
                - wxid: filehelper
                  msg: 消息4
                - wxid: filehelper
                  msg: 消息5
                - wxid: filehelper
                  msg: 消息6
      responses:
        '200':
          description: ''
          content:
            application/json:
              schema:
                type: object
                properties: {}
          headers: {}
          x-apifox-name: 成功
      security: []
      x-apifox-folder: ''
      x-apifox-status: developing
      x-run-in-apifox: https://app.apifox.com/web/project/8029877/apis/api-436536146-run
components:
  schemas: {}
  securitySchemes: {}
servers:
  - url: ''
    description: 开发环境
security: []

```