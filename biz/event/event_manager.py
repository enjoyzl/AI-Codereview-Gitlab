from blinker import Signal

from biz.entity.review_entity import MergeRequestReviewEntity, PushReviewEntity
from biz.service.review_service import ReviewService
from biz.utils.im import notifier

# 定义全局事件管理器（事件信号）
event_manager = {
    "merge_request_reviewed": Signal(),
    "push_reviewed": Signal(),
}


# 定义事件处理函数
def on_merge_request_reviewed(mr_review_entity: MergeRequestReviewEntity):
    # 发送IM消息通知
    im_msg = f"""
### 🔀 {mr_review_entity.project_name}: Merge Request

#### 合并请求信息:
- **提交者:** {mr_review_entity.author}

- **源分支**: {mr_review_entity.source_branch}
- **目标分支**: {mr_review_entity.target_branch}
- **更新时间**: {mr_review_entity.updated_at}
- **提交信息:** {mr_review_entity.commit_messages}

- [查看合并详情]({mr_review_entity.url})

- **AI Review 结果:** 

{mr_review_entity.review_result}
    """
    notifier.send_notification(content=im_msg, msg_type='markdown', title='Merge Request Review',
                               project_name=mr_review_entity.project_name, url_slug=mr_review_entity.url_slug,
                               webhook_data=mr_review_entity.webhook_data)

    # 记录到数据库
    ReviewService().insert_mr_review_log(mr_review_entity)


def on_push_reviewed(entity: PushReviewEntity):
    # 获取配置：是否使用text消息类型
    import os
    use_text_msg = os.environ.get('PUSH_WECOM_USE_TEXT_MSG', '0') == '1'
    msg_type = 'text' if use_text_msg else 'markdown'
    
    # 提取commit者用于@（text和markdown都支持）
    mentioned_list = None
    authors = set()
    for commit in entity.commits:
        author = commit.get('author', '')
        if author:
            authors.add(author)
    mentioned_list = list(authors) if authors else None
    
    # 发送IM消息通知
    if msg_type == 'text':
        # Text消息，提交信息保持详细，Review结果仅显示评分和链接
        im_msg = f"🚀 {entity.project_name}: Push\n\n"
        im_msg += "提交记录:\n"
        for commit in entity.commits:
            message = commit.get('message', '').strip()
            author = commit.get('author', 'Unknown Author')
            timestamp = commit.get('timestamp', '')
            url = commit.get('url', '#')
            im_msg += (
                f"- 提交信息: {message}\n"
                f"  提交者: {author}\n"
                f"  时间: {timestamp}\n"
                f"  查看详情: {url}\n\n"
            )
        
        if entity.review_result and entity.score > 0:
            im_msg += f"AI Review 结果:\n"
            im_msg += f"评分: {entity.score:.1f}/100\n"
            if entity.note_url:
                im_msg += f"查看详情: {entity.note_url}"
    else:
        # Markdown消息
        im_msg = f"### 🚀 {entity.project_name}: Push\n\n"
        im_msg += "#### 提交记录:\n"

        for commit in entity.commits:
            message = commit.get('message', '').strip()
            author = commit.get('author', 'Unknown Author')
            timestamp = commit.get('timestamp', '')
            url = commit.get('url', '#')
            im_msg += (
                f"- **提交信息**: {message}\n"
                f"- **提交者**: {author}\n"
                f"- **时间**: {timestamp}\n"
                f"- [查看提交详情]({url})\n\n"
            )

        if entity.review_result:
            im_msg += f"#### AI Review 结果:\n"
            im_msg += f"- **评分**: {entity.score:.1f}\n"
            if entity.note_url:
                im_msg += f"- [查看详情]({entity.note_url})\n\n"
            im_msg += f"{entity.review_result}\n\n"
    
    notifier.send_notification(
        content=im_msg, 
        msg_type=msg_type,
        title=f"{entity.project_name} Push Event",
        project_name=entity.project_name, 
        url_slug=entity.url_slug,
        webhook_data=entity.webhook_data,
        mentioned_list=mentioned_list
    )

    # 记录到数据库
    ReviewService().insert_push_review_log(entity)


# 连接事件处理函数到事件信号
event_manager["merge_request_reviewed"].connect(on_merge_request_reviewed)
event_manager["push_reviewed"].connect(on_push_reviewed)
