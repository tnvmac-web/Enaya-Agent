#!/usr/bin/env python3
"""
Enaya Agent - Pets/Mascots System
Animated mascots that react to agent activity across CLI, TUI, and desktop.
"""

from __future__ import animations
import asyncio
import os
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from enaya.gateway.runner import GatewayRunner


# =============================================================================
# Pet Data Classes
# =============================================================================

@dataclass
class PetState:
    """Current state of a pet."""
    name: str
    mood: str = "happy"  # happy, sad, excited, sleeping, thinking, working
    energy: float = 1.0  # 0.0 to 1.0
    hunger: float = 0.0  # 0.0 to 1.0
    xp: int = 0
    level: int = 1
    last_interaction: float = 0


@dataclass
class PetAnimation:
    """Animation frame data."""
    frames: list[str]
    frame_duration: float = 0.1
    loop: bool = True


# =============================================================================
# Pet Base Class
# =============================================================================

class PetBase(ABC):
    """Base class for pet mascots."""
    
    def __init__(self, name: str):
        self.name = name
        self.state = PetState(name=name)
        self._running = False
        self._animation_task: Optional[asyncio.Task] = None
        self._listeners: list[Callable] = []
    
    @abstractmethod
    def get_idle_frames(self) -> list[str]:
        """Get idle animation frames."""
        pass
    
    @abstractmethod
    def get_mood_frames(self, mood: str) -> list[str]:
        """Get frames for a specific mood."""
        pass
    
    @abstractmethod
    def get_action_frames(self, action: str) -> list[str]:
        """Get frames for a specific action."""
        pass
    
    def get_frame(self, mood: str = None, action: str = None) -> str:
        """Get current frame based on state."""
        if action:
            frames = self.get_action_frames(action)
        elif mood:
            frames = self.get_mood_frames(mood)
        else:
            frames = self.get_idle_frames()
        
        if not frames:
            frames = self.get_idle_frames()
        
        # Simple frame selection based on time
        import time
        frame_idx = int(time.time() * 10) % len(frames)
        return frames[frame_idx]
    
    async def start(self) -> None:
        """Start pet animation loop."""
        self._running = True
        self._animation_task = asyncio.create_task(self._animation_loop())
    
    async def stop(self) -> None:
        """Stop pet animation."""
        self._running = False
        if self._animation_task:
            self._animation_task.cancel()
            try:
                await self._animation_task
            except asyncio.CancelledError:
                pass
    
    async def _animation_loop(self) -> None:
        """Main animation loop."""
        while self._running:
            # Update state based on time
            self._update_state()
            
            # Notify listeners
            frame = self.get_frame(mood=self.state.mood)
            for listener in self._listeners:
                try:
                    listener(self, frame, self.state)
                except Exception:
                    pass
            
            await asyncio.sleep(0.1)
    
    def _update_state(self) -> None:
        """Update pet state over time."""
        import time
        now = time.time()
        
        # Decrease energy over time
        if self.state.energy > 0:
            self.state.energy = max(0, self.state.energy - 0.001)
        
        # Increase hunger over time
        if self.state.hunger < 1:
            self.state.hunger = min(1, self.state.hunger + 0.0005)
        
        # Auto-mood changes
        if self.state.energy < 0.2:
            self.state.mood = "sleeping"
        elif self.state.hunger > 0.8:
            self.state.mood = "sad"
        elif self.state.energy > 0.8 and self.state.hunger < 0.3:
            self.state.mood = "happy"
    
    def add_listener(self, callback: Callable) -> None:
        """Add state change listener."""
        self._listeners.append(callback)
    
    def remove_listener(self, callback: Callable) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)
    
    def interact(self, interaction: str) -> dict:
        """Handle user interaction."""
        import time
        self.state.last_interaction = time.time()
        
        if interaction == "pet":
            self.state.mood = "happy"
            self.state.energy = min(1, self.state.energy + 0.1)
            self.state.xp += 5
        elif interaction == "feed":
            self.state.hunger = max(0, self.state.hunger - 0.3)
            self.state.mood = "happy"
            self.state.xp += 3
        elif interaction == "play":
            self.state.mood = "excited"
            self.state.energy = max(0, self.state.energy - 0.1)
            self.state.xp += 10
        elif interaction == "work":
            self.state.mood = "thinking"
            self.state.energy = max(0, self.state.energy - 0.05)
            self.state.xp += 1
        
        # Level up check
        new_level = (self.state.xp // 100) + 1
        if new_level > self.state.level:
            self.state.level = new_level
            return {"leveled_up": True, "new_level": new_level}
        
        return {"leveled_up": False, "level": self.state.level}
    
    def get_status(self) -> dict:
        """Get current pet status."""
        return {
            "name": self.name,
            "mood": self.state.mood,
            "energy": round(self.state.energy * 100),
            "hunger": round(self.state.hunger * 100),
            "xp": self.state.xp,
            "level": self.state.level,
            "frame": self.get_frame(mood=self.state.mood),
        }


# =============================================================================
# Built-in Pets
# =============================================================================

class EnayaBot(PetBase):
    """Default Enaya bot mascot."""
    
    def get_idle_frames(self) -> list[str]:
        return [
            "🤖",
            "🤖 ",
            " 🤖",
        ]
    
    def get_mood_frames(self, mood: str) -> list[str]:
        frames = {
            "happy": ["🤖😊", "🤖😄", "🤖😃"],
            "sad": ["🤖😢", "🤖😭", "🤖😞"],
            "excited": ["🤖🎉", "🤖✨", "🤖🚀"],
            "sleeping": ["🤖😴", "🤖💤", "🤒💤"],
            "thinking": ["🤖🤔", "🤖💭", "🤖🧠"],
            "working": ["🤖⚙️", "🤖🔧", "🤖⚡"],
        }
        return frames.get(mood, self.get_idle_frames())
    
    def get_action_frames(self, action: str) -> list[str]:
        frames = {
            "pet": ["🤖😊", "🤖😍", "🤖🥰"],
            "feed": ["🤖🍎", "🤖🍕", "🤖🍪"],
            "play": ["🤖🎮", "🤖🎲", "🤖🎪"],
            "work": ["🤖💻", "🤖📝", "🤖🔍"],
        }
        return frames.get(action, self.get_idle_frames())


class CodeCat(PetBase):
    """Code cat mascot."""
    
    def get_idle_frames(self) -> list[str]:
        return [
            "🐱",
            "🐱 ",
            " 🐱",
        ]
    
    def get_mood_frames(self, mood: str) -> list[str]:
        frames = {
            "happy": ["🐱😺", "🐱😸", "🐱😹"],
            "sad": ["🐱😿", "🐱😾", "🐱🙀"],
            "excited": ["🐱🎉", "🐱✨", "🐱🎊"],
            "sleeping": ["🐱😴", "🐱💤", "🐱💤"],
            "thinking": ["🐱🤔", "🐱💭", "🐱🧠"],
            "working": ["🐱⌨️", "🐱🖥️", "🐱💻"],
        }
        return frames.get(mood, self.get_idle_frames())
    
    def get_action_frames(self, action: str) -> list[str]:
        frames = {
            "pet": ["🐱😺", "🐱😽", "🐱😻"],
            "feed": ["🐱🐟", "🐱🥛", "🐱🍖"],
            "play": ["🐱🧶", "🐱🎯", "🐱🎮"],
            "work": ["🐱💻", "🐱📝", "🐱🔍"],
        }
        return frames.get(action, self.get_idle_frames())


class RocketRaccoon(PetBase):
    """Rocket raccoon mascot."""
    
    def get_idle_frames(self) -> list[str]:
        return [
            "🦝",
            "🦝 ",
            " 🦝",
        ]
    
    def get_mood_frames(self, mood: str) -> list[str]:
        frames = {
            "happy": ["🦝😃", "🦝😄", "🦝😁"],
            "sad": ["🦝😢", "🦝😞", "🦝😔"],
            "excited": ["🦝🚀", "🦝🌟", "🦝✨"],
            "sleeping": ["🦝😴", "🦝💤", "🦝💤"],
            "thinking": ["🦝🤔", "🦝💭", "🦝🧠"],
            "working": ["🦝🔧", "🦝⚙️", "🦝🛠️"],
        }
        return frames.get(mood, self.get_idle_frames())
    
    def get_action_frames(self, action: str) -> list[str]:
        frames = {
            "pet": ["🦝😊", "🦝🤗", "🦝😍"],
            "feed": ["🦝🍎", "🦝🌰", "🦝🍯"],
            "play": ["🦝🎯", "🦝🎲", "🦝🎮"],
            "work": ["🦝🔧", "🦝🛠️", "🦝⚙️"],
        }
        return frames.get(action, self.get_idle_frames())


class TerminalTurtle(PetBase):
    """Terminal turtle mascot."""
    
    def get_idle_frames(self) -> list[str]:
        return [
            "🐢",
            "🐢 ",
            " 🐢",
        ]
    
    def get_mood_frames(self, mood: str) -> list[str]:
        frames = {
            "happy": ["🐢😊", "🐢😄", "🐢😃"],
            "sad": ["🐢😢", "🐢😞", "🐢😔"],
            "excited": ["🐢🎉", "🐢✨", "🐢🚀"],
            "sleeping": ["🐢😴", "🐢💤", "🐢💤"],
            "thinking": ["🐢🤔", "🐢💭", "🐢🧠"],
            "working": ["🐢⌨️", "🐢💻", "🐢🖥️"],
        }
        return frames.get(mood, self.get_idle_frames())
    
    def get_action_frames(self, action: str) -> list[str]:
        frames = {
            "pet": ["🐢😊", "🐢😽", "🐢😻"],
            "feed": ["🐢🥬", "🐢🌿", "🐢🍓"],
            "play": ["🐢🏀", "🐢🎯", "🐢🎮"],
            "work": ["🐢💻", "🐢📝", "🐢🔍"],
        }
        return frames.get(action, self.get_idle_frames())


# =============================================================================
# Pet Manager
# =============================================================================

class PetManager:
    """Manages pet mascots across surfaces."""
    
    def __init__(self):
        self.pets: dict[str, PetBase] = {
            "enaya": EnayaBot("Enaya"),
            "cat": CodeCat("CodeCat"),
            "raccoon": RocketRaccoon("Rocket"),
            "turtle": TerminalTurtle("Turtle"),
        }
        self.active_pet: Optional[PetBase] = self.pets["enaya"]
        self._listeners: list[Callable] = []
    
    def get_pet(self, name: str) -> Optional[PetBase]:
        return self.pets.get(name)
    
    def set_active(self, name: str) -> bool:
        if name in self.pets:
            self.active_pet = self.pets[name]
            return True
        return False
    
    def get_active(self) -> Optional[PetBase]:
        return self.active_pet
    
    def list_pets(self) -> list[dict]:
        return [
            {"name": name, "active": pet == self.active_pet}
            for name, pet in self.pets.items()
        ]
    
    async def start_all(self) -> None:
        for pet in self.pets.values():
            await pet.start()
    
    async def stop_all(self) -> None:
        for pet in self.pets.values():
            await pet.stop()
    
    def interact(self, interaction: str) -> dict:
        if self.active_pet:
            return self.active_pet.interact(interaction)
        return {"error": "No active pet"}
    
    def get_status(self) -> dict:
        if self.active_pet:
            return self.active_pet.get_status()
        return {"error": "No active pet"}
    
    def add_listener(self, callback: Callable) -> None:
        for pet in self.pets.values():
            pet.add_listener(callback)
    
    def get_frame(self) -> str:
        if self.active_pet:
            return self.active_pet.get_frame(mood=self.active_pet.state.mood)
        return "🤖"


# =============================================================================
# CLI Integration
# =============================================================================

_pet_manager: Optional[PetManager] = None


def get_pet_manager() -> PetManager:
    global _pet_manager
    if _pet_manager is None:
        _pet_manager = PetManager()
    return _pet_manager


async def pet_interact(interaction: str) -> dict:
    manager = get_pet_manager()
    return manager.interact(interaction)


async def pet_status() -> dict:
    manager = get_pet_manager()
    return manager.get_status()


async def pet_list() -> list[dict]:
    manager = get_pet_manager()
    return manager.list_pets()


async def pet_set(name: str) -> bool:
    manager = get_pet_manager()
    return manager.set_active(name)


async def pet_start() -> None:
    manager = get_pet_manager()
    await manager.start_all()


async def pet_stop() -> None:
    manager = get_pet_manager()
    await manager.stop_all()