"""
Main Telegram Casino Bot Implementation
Handles bot initialization, command routing, and application lifecycle
"""

import logging
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from database import DatabaseManager
from handlers import CommandHandlers
bot_token = "7553801366:AAEm2NfyEtP2Qi0PJJCpGc1VPmhksxN7OAw"

logger = logging.getLogger(__name__)

class CasinoBot:
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.db_manager = DatabaseManager()
        self.handlers = CommandHandlers(self.db_manager)
        self.application = None
    
    async def start(self):
        """Start the casino bot"""
        try:
            # Create application
            self.application = Application.builder().token(self.bot_token).build()
            
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.handlers.start_command))
            self.application.add_handler(CommandHandler("help", self.handlers.help_command))
            self.application.add_handler(CommandHandler("games", self.handlers.games_command))
            self.application.add_handler(CommandHandler("balance", self.handlers.balance_command))
            self.application.add_handler(CommandHandler("topup", self.handlers.topup_command))
            self.application.add_handler(CommandHandler("history", self.handlers.history_command))
            self.application.add_handler(CommandHandler("stats", self.handlers.stats_command))
            
            # Add quick game command handlers
            self.application.add_handler(CommandHandler("darts", self._quick_darts))
            self.application.add_handler(CommandHandler("slots", self._quick_slots))
            self.application.add_handler(CommandHandler("dice", self._quick_dice))
            self.application.add_handler(CommandHandler("blackjack", self._quick_blackjack))
            
            # Add callback query handler for inline buttons
            self.application.add_handler(CallbackQueryHandler(self.handlers.button_callback))
            
            # Add message handler for unknown commands
            self.application.add_handler(MessageHandler(filters.COMMAND, self._unknown_command))
            
            logger.info("Starting Casino Bot...")
            
            # Start the bot
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            logger.info("Casino Bot is running!")
            
            # Keep the bot running
            await self.application.updater.idle()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
        finally:
            if self.application:
                await self.application.stop()
    
    async def _quick_darts(self, update, context):
        """Quick darts game command"""
        user_id = str(update.effective_user.id)
        
        try:
            from config import GAME_PRICES
            
            if not self.db_manager.can_afford_game(user_id, GAME_PRICES['darts']):
                await update.message.reply_text(
                    f"❌ Insufficient balance for darts!\n"
                    f"Cost: ${GAME_PRICES['darts']}\n"
                    f"Your balance: ${self.db_manager.get_balance(user_id)}\n\n"
                    f"Use /topup to add funds."
                )
                return
            
            # Deduct cost and play
            self.db_manager.deduct_game_cost(user_id, GAME_PRICES['darts'], 'darts')
            result = self.handlers.games.play_darts()
            
            if result['is_winner']:
                winnings = result['winnings']
                self.db_manager.add_game_winnings(user_id, winnings, 'darts', result['zone'])
                result_text = f"🎯 **DARTS** 🎯\n\n{result['result_text']}\n\n🎉 **YOU WON ${winnings}!**"
            else:
                result_text = f"🎯 **DARTS** 🎯\n\n{result['result_text']}\n\n😔 Better luck next time!"
            
            balance = self.db_manager.get_balance(user_id)
            result_text += f"\n\n💰 Balance: **${balance}**"
            
            await update.message.reply_text(result_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error playing darts: {str(e)}")
    
    async def _quick_slots(self, update, context):
        """Quick slots game command"""
        user_id = str(update.effective_user.id)
        
        try:
            from config import GAME_PRICES
            
            if not self.db_manager.can_afford_game(user_id, GAME_PRICES['slots']):
                await update.message.reply_text(
                    f"❌ Insufficient balance for slots!\n"
                    f"Cost: ${GAME_PRICES['slots']}\n"
                    f"Your balance: ${self.db_manager.get_balance(user_id)}\n\n"
                    f"Use /topup to add funds."
                )
                return
            
            # Deduct cost and play
            self.db_manager.deduct_game_cost(user_id, GAME_PRICES['slots'], 'slots')
            result = self.handlers.games.play_slots()
            
            if result['is_winner']:
                winnings = result['winnings']
                self.db_manager.add_game_winnings(user_id, winnings, 'slots', result['win_type'])
                result_text = f"🎰 **SLOTS** 🎰\n\n{result['result_text']}\n\n🎉 **YOU WON ${winnings}!**"
            else:
                result_text = f"🎰 **SLOTS** 🎰\n\n{result['result_text']}\n\n😔 No win this time!"
            
            balance = self.db_manager.get_balance(user_id)
            result_text += f"\n\n💰 Balance: **${balance}**"
            
            await update.message.reply_text(result_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error playing slots: {str(e)}")
    
    async def _quick_dice(self, update, context):
        """Quick dice game command"""
        user_id = str(update.effective_user.id)
        
        try:
            from config import GAME_PRICES
            
            # Check if user provided a guess
            if not context.args or len(context.args) != 1:
                await update.message.reply_text(
                    f"🎲 **DICE GAME** 🎲\n\n"
                    f"Usage: /dice <guess>\n"
                    f"Example: /dice 3\n\n"
                    f"Guess a number between 1-6 and win 2x your bet!\n"
                    f"Cost: ${GAME_PRICES['dice']}"
                )
                return
            
            try:
                guess = int(context.args[0])
                if guess not in range(1, 7):
                    raise ValueError("Guess must be between 1 and 6")
            except ValueError:
                await update.message.reply_text("❌ Please provide a valid number between 1 and 6!")
                return
            
            if not self.db_manager.can_afford_game(user_id, GAME_PRICES['dice']):
                await update.message.reply_text(
                    f"❌ Insufficient balance for dice!\n"
                    f"Cost: ${GAME_PRICES['dice']}\n"
                    f"Your balance: ${self.db_manager.get_balance(user_id)}\n\n"
                    f"Use /topup to add funds."
                )
                return
            
            # Deduct cost and play
            self.db_manager.deduct_game_cost(user_id, GAME_PRICES['dice'], 'dice')
            result = self.handlers.games.play_dice(guess)
            
            if result['is_winner']:
                winnings = result['winnings']
                self.db_manager.add_game_winnings(user_id, winnings, 'dice', f"Guessed {guess}")
                result_text = f"🎲 **DICE** 🎲\n\n{result['result_text']}\n\n🎉 **CORRECT! YOU WON ${winnings}!**"
            else:
                result_text = f"🎲 **DICE** 🎲\n\n{result['result_text']}\n\n😔 Wrong guess! Better luck next time!"
            
            balance = self.db_manager.get_balance(user_id)
            result_text += f"\n\n💰 Balance: **${balance}**"
            
            await update.message.reply_text(result_text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Error playing dice: {str(e)}")
    
    async def _quick_blackjack(self, update, context):
        """Quick blackjack game command"""
        await update.message.reply_text(
            "🃏 **BLACKJACK** 🃏\n\n"
            "Blackjack requires interactive gameplay!\n"
            "Use /games to start a blackjack session with hit/stand options.\n\n"
            f"Cost: ${self.handlers.__class__.__dict__.get('GAME_PRICES', {}).get('blackjack', '1.00')} per game"
        )
    
    async def _unknown_command(self, update, context):
        """Handle unknown commands"""
        await update.message.reply_text(
            "❓ Unknown command!\n\n"
            "Available commands:\n"
            "/start - Get started\n"
            "/games - Play games\n"
            "/balance - Check balance\n"
            "/topup - LTC top-up info\n"
            "/help - Show help\n\n"
            "Quick games:\n"
            "/darts - Play darts\n"
            "/slots - Play slots\n"
            "/dice <1-6> - Play dice\n"
            "/blackjack - Play blackjack"
        )
