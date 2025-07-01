from bot.services import handle_vote_callback_task


async def handle_vote_callback(update, context):
    """Обрабатывает нажатие на кнопки голосования."""
    data = update.callback_query.data
    user = update.callback_query.from_user

    await handle_vote_callback_task(update.callback_query.id, data, user.id,
                                    user.username or user.full_name)
