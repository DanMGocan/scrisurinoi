class Config:
    # Post creation costs by category
    POST_COSTS = {
        'poetry': 5,
        'story': 10,
        'essay': 8,
        'theater': 12,
        'letter': 5,
        'journal': 3
    }
    
    POST_WORD_LIMIT = 300  # Word limit before additional costs
    POST_WORD_COST_MULTIPLIER = 2  # Cost multiplier for exceeding word limit
    
    # Points for likes
    POST_LIKE_REWARD = 2  # Points awarded to post author for receiving a like
    COMMENT_LIKE_REWARD = 1  # Points awarded to comment author for receiving a like
    LIKE_GIVEN_REWARD = 1  # Points awarded for giving a like
    
    # Points for comments based on quality
    COMMENT_QUALITY_REWARDS = {
        'low': 1,     # 0-33 score
        'medium': 2,  # 34-66 score
        'high': 3     # 67-100 score
    }
    
    # Comment quality thresholds
    COMMENT_QUALITY_THRESHOLDS = {
        'low': 33,
        'medium': 66
    }
    
    # Points for daily activities
    DAILY_LOGIN_REWARD = 1  # Points for logging in (once per day)
    DAILY_MEMBERSHIP_REWARD = 1  # Points for each day of membership
