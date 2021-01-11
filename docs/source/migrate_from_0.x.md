# Migrate from MCDR 0.x

## File structure

Since MCDR now is installed as a python package, unless you run MCDR with source, file / folders below can be removed

- utils/
- resources/
- requirements.txt
- LICENSE
- readme.md
- readme_cn.md

The logging folder is renamed from `log/` to `logs/`

## Config

There come quite a lot of changes to the config file. Although MCDR will still work if you keep the old config file, it's highly recommend to make a new default configure file, and fill your old configures into the new configure file.

You can rename the old `config.yml` to a temporary name like `old_config.yml`, then start MCDR. MCDR will generate a new default configure file and exit. Then open these 2 configure file and migrate.

## Permission

There's no change to the permission system and the permission file, so you can just use the old permission file.

## Plugins

Most of the MCDR 0.x plugins only need to have some small changes to be adjusted to current MCDR. Some of them can even directly work with current MCDR without any change.

### Metadata

Metadata is a global field inside the plugin file. It's used to store basic information and dependencies of a plugin. It's necessary for a plugin to declare it so MCDR can handle all the plugins correctly.

A legacy plugin is still able to be loaded if it doesn't have the metadata field, but a warning will be shown in the console.

Check [here]() for more information about plugin metadata

### Listener

#### Compatibility

Current MCDR implements a better event & listener system, plugin can register any callback as event listener to any event. 

Most of the MCDR 0.x style event listeners are reserved and now work as an automatically registered default listener for the related event.

- on_info
- on_user_info
- on_server_startup
- on_server_stop
- on_mcdr_stop
- on_player_joined
- on_player_left

If you declare a function with name above, MCDR will automatically detect it and register it as an event listener when your plugin gets loaded. The listener priority is the default value `1000`

These 2 events are removed from MCDR

- on_death_message
- on_player_made_advancement

If your plugin relies on these 2 events, there is an alternative for it: [coming-soon]()

#### Listener arguments

In MCDR 0.x the player joined event listener accepts 2 or 3 arguments. The 2 definitions below work

```python
def on_player_joined(server: ServerInterface, player: str):
    pass

def on_player_joined(server: ServerInterface, player: str, info: Info):
    pass
```

However, the former usage is removed in current MCDR version, only the latter one with 3 arguments is accepted.

Beside the player joined event listener, other event listener callbacks have their argument list unchanged.

### Multi-threading

MCDR 0.x allocates separate threads for plugins to execute their event listener callbacks. This lazyness brings unpredictable plugin execution order and affects overall performance by a lot. Multithreading also make it hard to do something after all plugins have finished their callbacks.

In current MCDR, all event listeners callbacks are invoked in a single thread named `TaskExecutor` to solve the issues above.

If your plugin depends on multithreading from MCDR to do some parallel operations, or your plugin need to do some I/O or network operations which might take some times, you'd better create a new thread to execute them manually, so MCDR won't be blocked by these.

MCDR also provides a simple function decorator `new_thread` for lazy man, to make a function multi threaded when being invoked. Here's an quick example:

```python
from mcdreforged.api.decorator import *

# undecorated function
def my_slow_method1():
    time.sleep(10)

@new_thread  # decorated function, will run at a new thread
def my_slow_method2():
    time.sleep(10)

@new_thread('MyThread')  # specify the thread name
def my_slow_method3():
    time.sleep(10)
```

With the `@new_thread` decorator, everytime when you invoke `my_slow_method2`, a new daemon thread will be started to executed it. The `new_thread` decorator only changed the return value to the created thread instance of the function. Beside the return value, it reserved all signature of the decorated function, so you can safely use the decorated function as if there's no decorating at all.

### Package location

If your plugin imports some of the mcdr utils, like `RText` or `Rcon`, you need to take a look at the package location.

Current MCDR collects all useful classes / functions in the `mcdreforged.api` package. It's recommended to import the package you want in this `api` package.

Use `from mcdreforged.api.rtext import *` if you want to use all rtext classes

Use `from mcdreforged.api.rcon import *` if you want to use all rcon classes. Class `Rcon` is renamed to `RconConnection` by the way

For lazy man, you can safely use `from mcdreforged.api.all import *` to import all useful things to the plugin