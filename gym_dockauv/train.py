import os
import logging

import numpy as np
import pygame

import gym
from matplotlib import pyplot as plt
from stable_baselines3 import A2C, PPO

from gym_dockauv.utils.datastorage import EpisodeDataStorage, FullDataStorage
from gym_dockauv.config.PPO_hyperparams import PPO_HYPER_PARAMS_DEFAULT

# Set logger
logger = logging.getLogger(__name__)


def train(total_timesteps: int,
          model_save_path: str = "logs/PPO_docking",
          agent_hyper_params: dict = PPO_HYPER_PARAMS_DEFAULT,
          tb_log_name: str = "PPO",
          timesteps_per_save: int = None,
          model_load_path: str = None) -> None:
    f"""
    Function to train and save model, own wrapper
    
    Model name that will be saved is "[model_save_path]_[elapsed_timesteps]", when timesteps_per_save is given model 
    is captured and saved in between 
    
    .. note:: Interval of saving and number of total runtime might be inaccurate, if the StableBaseLine agent n_steps 
        is not accordingly updated, for example total runtime is 3000 steps, however, update per n_steps of the agent is 
        by default for PPO at 2048, thus the agents only checks if its own simulation time steps is bigger than 3000 
        after every multiple of 2048 

    :param total_timesteps: total timesteps for this training run
    :param model_save_path: path where to save the model
    :param agent_hyper_params: agent hyper parameter, default is always loaded
    :param tb_log_name: log file name of this run for tensor board
    :param timesteps_per_save: simulation timesteps before saving the model in that interval
    :param model_load_path: path of existing model, use to continue training with that model
    :return: None
    """
    # Create environment
    env = gym.make("docking3d-v0")
    # Init variables
    elapsed_timesteps = 0
    sim_timesteps = timesteps_per_save if timesteps_per_save else total_timesteps

    # Instantiate the agent
    if model_load_path is None:
        model = PPO(policy='MlpPolicy', env=env, **agent_hyper_params)
    else:
        # Note that this does not load a replay buffer
        model = PPO.load(model_load_path, env=env)

    while elapsed_timesteps < total_timesteps:
        # Train the agent
        model.learn(total_timesteps=sim_timesteps, reset_num_timesteps=False, tb_log_name=tb_log_name)
        # Taking the actual elapsed timesteps here, so the total simulation time at least will not be biased
        elapsed_timesteps = model.num_timesteps
        # Save the agent
        tmp_model_save_path = f"{model_save_path}_{elapsed_timesteps}"
        # This DOES NOT save the replay/rollout buffer, that is why we continue using the same model instead of
        # reloading anything in the while loop
        model.save(tmp_model_save_path)
        logger.info(f'Successfully saved model: {os.path.join(os.path.join(os.getcwd(), tmp_model_save_path))}')

    # TODO: Check if saving rollout buffer is worth it
    env.save_full_data_storage()


def predict(model_path: str):
    env = gym.make("docking3d-v0")
    # Load the trained agent
    # NOTE: if you have loading issue, you can pass `print_system_info=True`
    # to compare the system on which the model was trained vs the current one
    # model = DQN.load("dqn_lunar", env=env, print_system_info=True)
    model = PPO.load(model_path, env=env)

    # Evaluate the agent
    # NOTE: If you use wrappers with your environment that modify rewards,
    #       this will be reflected here. To evaluate with original rewards,
    #       wrap environment in a "Monitor" wrapper before other wrappers.
    # mean_reward, std_reward = evaluate_policy(model, model.get_env(), n_eval_episodes=10)

    # Enjoy trained agent
    obs = env.reset(seed=5)
    for i in range(1000):
        action, _states = model.predict(obs, deterministic=True)
        print(action)
        obs, rewards, dones, info = env.step(action)
        env.render()


def post_analysis_directory(directory: str = "/home/erikx3/PycharmProjects/gym_dockauv/logs"):
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        # Capture full data pkl file
        full_path = os.path.join(directory, filename)
        if filename.endswith("FULL_DATA_STORAGE.pkl"):
            full_stor = FullDataStorage()
            full_stor.load(full_path)
            full_stor.plot_rewards()
            plt.show()
        # Episode Data Storage:
        elif filename.endswith(".pkl"):
            epi_stor = EpisodeDataStorage()
            epi_stor.load(full_path)
            epi_stor.plot_epsiode_states_and_u()
            epi_stor.plot_rewards()
            plt.show()
            # epi_stor.plot_episode_animation(t_per_step=None, title="Test Post Flight Visualization")


def manual_control():
    """
    Function with pygame workaround to manually fly and debug the vehicle

    Great for debugging purposes, since post analysis can be called on the log that is created
    """
    # Settings:
    WINDOW_X = 400
    WINDOW_Y = 400
    # Init environment
    env = gym.make("docking3d-v0")
    env.reset()
    # Init pygame
    pygame.init()
    window = pygame.display.set_mode((WINDOW_X, WINDOW_Y))
    run = True
    # Init pygame text I want to use
    pygame.font.init()
    my_font = pygame.font.SysFont('Comic Sans MS', 30)
    text_title = my_font.render('Click on this window to control vehicle', False, (255, 255, 255))
    text_note = my_font.render('Note: Not real time!', False, (255, 255, 255))
    text_instructions = [my_font.render('Linaer x: [w, s]', False, (255, 255, 255)),
                         my_font.render('Linaer y: [a, d]', False, (255, 255, 255)),
                         my_font.render('Linaer z: [r, f]', False, (255, 255, 255)),
                         my_font.render('Angular x: [u, j]', False, (255, 255, 255)),
                         my_font.render('Angular y: [h, k]', False, (255, 255, 255)),
                         my_font.render('Angular z: [o, l]', False, (255, 255, 255))]

    while run:
        # Text on pygame window
        window.blit(text_title, (0, 0))
        window.blit(text_note, (0, 30))
        pos = 60
        for text in text_instructions:
            window.blit(text, (0, pos))
            pos += 30
        pygame.display.update()
        pygame.display.flip()

        # Derive action from keyboard input
        action = np.zeros(6)
        keys = pygame.key.get_pressed()
        action[0] = (keys[pygame.K_w] - keys[pygame.K_s]) * 1
        action[1] = (keys[pygame.K_a] - keys[pygame.K_d]) * 1
        action[2] = (keys[pygame.K_f] - keys[pygame.K_r]) * 1
        action[3] = (keys[pygame.K_u] - keys[pygame.K_j]) * 1
        action[4] = (keys[pygame.K_h] - keys[pygame.K_k]) * 1
        action[5] = (keys[pygame.K_o] - keys[pygame.K_l]) * 1
        # Need this part below to make everything work
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    # pygame.quit()
                    run = False
        print(action)

        # Env related stuff
        obs, rewards, dones, info = env.step(action)
        env.render()

    env.reset()
