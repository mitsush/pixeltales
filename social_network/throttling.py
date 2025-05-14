from rest_framework.throttling import UserRateThrottle

class PostUserRateThrottle(UserRateThrottle):
    rate = '100/day'
    scope = 'posts'

class CommentUserRateThrottle(UserRateThrottle):
    rate = '200/day'
    scope = 'comments'