# Copyright: Krzysztof Kowalczyk
# Owner: Krzysztof Kowalczyk

# This file contains symbolic names of all errors returned by ipedia server

# return serverFailure if we encountered a problem in code execution
# (e.g. exception has been thrown that shouldn't have). Usually it means
# there's a bug in our code
serverFailure = 1

# return unsupportedDevice if device info sent with Get-Cookie is not valid
unsupportedDevice = 2

# return invalidRegCode if the reg code is invalid
invalidRegCode = 3

# request from the client has been malformed. This applies to cases when
# the request doesn't fit our strict format of request
malformedRequest = 4

# user has reached lookup limit for unregistered version 
lookupLimitReached = 5

# returned if request field is not known by the server as something that
# client might send
invalidRequest = 6

# return unexpectedRequestArgument if a given request doesn't use arguments
# but client has sent it
unexpectedRequestArgument = 7

# return requestArgumentMissing if a given request requres an argument
# but client didn't send one
requestArgumentMissing = 8

# return invalidProtocolVersion if the value of protocolVersionField is
# not something we handle
invalidProtocolVersion = 9

# return invalidCookie if users sends cookie that hasn't been generated
# by the server
invalidCookie = 10

# return userDisabled if user is marked as disabled (based on cookie or
# regCode client sends)
userDisabled = 11

# return forceUpgrade if we want to force user to upgrade the software.
# Client will display apropriate dialog notyfing about the need to upgrade
# This is to make our life easier e.g. if we discover a fatal flaw in the
# software or if we don't want to support multiple versions
# of the protocol/data formats we can use this
forceUpgrade = 12

