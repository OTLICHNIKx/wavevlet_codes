from research.config import DEFAULT_RESEARCH_CONFIG
from research.dataset import build_all_datasets, ebn0_db_to_sigma


config = DEFAULT_RESEARCH_CONFIG

datasets = build_all_datasets(
    message_count=5,
    codes=config.codes,
    message_seed=config.message_seed,
    noise_seed=config.noise_seed,
)

for name, dataset in datasets.items():
    code_config = dataset.code_config
    code_rate = code_config.k / code_config.n
    sigma = ebn0_db_to_sigma(
        ebn0_db=1.0,
        code_rate=code_rate,
    )

    print()
    print(name)
    print("message_seed =", dataset.message_seed)
    print("noise_seed =", dataset.noise_seed)
    print("messages shape =", dataset.messages.shape)
    print("base_noise shape =", dataset.base_noise.shape)
    print("first message =", dataset.messages[0].tolist())
    print("first noise row first 5 =", dataset.base_noise[0, :5])
    print("sigma at Eb/N0 = 1 dB:", round(sigma, 6))