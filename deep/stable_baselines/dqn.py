import torch
from stable_baselines3 import DQN

from deep.stable_baselines.train import train
from deep.stable_baselines.util import ModelSettings, get_basic_train_settings
from deep.stable_baselines.policy.council_feature import CustomCombinedExtractor
from stable_baselines3.her.her_replay_buffer import HerReplayBuffer

class DQNModelSettings(ModelSettings):
    ...


train_envs = get_basic_train_settings(name="DQN")
train_envs.update(
    {
        "expname": "no-text-embedding",
        "total_timesteps": int(3e5),
        "checkpoint_freq": int(10e4),
        "eval_freq": int(10e4),
        "n_envs": 4
    }
)

model_envs: DQNModelSettings = {
    "policy": "MlpPolicy",
    "learning_rate": 0.0003,
    "seed": 37,
    "kwargs": {
        "batch_size": 128,
        "tau": 0.5,
        "gamma": 0.99,
        "train_freq": 4,
        "policy_kwargs": {
            "activation_fn": torch.nn.ReLU,
            "net_arch": [128, 128],
            # "features_extractor_class":CustomCombinedExtractor,
            # "features_extractor_kwargs":dict(),
        },
        "tensorboard_log": "./logs/tb/",
        "verbose": 1,
    },
}


if __name__ == "__main__":
    train(train_envs, model_envs, DQN)
