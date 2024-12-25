import torch
from torch import nn
from torch.nn import functional as F
import os
os.chdir(r'c:\\Users\\W\\Desktop\\Time-Series-Library')
import numpy as np

from args import args
import dataset_loader
import math
import tqdm
import random

import sys
sys.path.append(r"c:\\Users\\W\\Desktop\\Time-Series-Library")  # 将高一级目录添加到模块搜索路径
from process import Trainer,RayTrainer,WandBTrainer
from models import TimesNet, PatchTST 

import wandb

def seed_everything(seed):

    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.enabled = True


def prepare_data(args):

    
    # 加载数据集
    print("正在加载数据集...")
    seq_len, num_classes, num_channel, train_loader, val_loader, test_loader = dataset_loader.load_data(args)

    print(f"数据集名称: {args.dataset_name}")
    print(f"数据形状: ({seq_len},{num_channel})")

    print("数据集加载完成!")
    return seq_len, num_classes, num_channel, train_loader, val_loader, test_loader


def main():

    # 初始化模型
    print("正在初始化模型...")
    model = PatchTST.Model(args).to(args.device)  # 将模型移动到指定设备
    print(f"模型参数量: {sum(p.numel() for p in model.parameters() if p.requires_grad)}")

    print("模型初始化完成!")
    print("="*50)

    # 初始化训练器
    print("正在初始化训练器...")
    sys.path.append(r"c:\\Users\\W\\Desktop\\Time-Series-Library\\my_run")  # 将高一级目录添加到模块搜索路径
    trainer = Trainer(args, model, train_loader, test_loader, verbose=True)
    print("训练器初始化完成!")
    print("="*50)

    # 设置训练模式
    if args.is_training:
        # 开始训练
        print("开始训练模型...")
        best_metric,current_loss = trainer.train()
        
    else:
        # 加载最佳模型
        print("正在加载最佳模型...")
        model.load_state_dict(torch.load(args.save_path + '/model.pkl'))
        print("最佳模型加载完成!")
        print("="*50)

        # 开始测试
        print("开始测试模型...")
        trainer.eval_model_vqvae()
        print("模型测试完成!")


def train_wandb():
    wandb.init(project="HAR-B", entity=f"{args.model}-{args.dataset_name}")
    for key in wandb.config.keys():
        setattr(args, key, wandb.config[key])


    seq_len, num_classes, num_channel, train_loader, val_loader, test_loader = prepare_data(args=args)
    args.seq_len = seq_len
    args.enc_in = num_channel
    args.num_class = num_classes

    # 初始化模型    
    print("正在初始化模型...")
    model = TimesNet.Model(args).to(args.device)  # 将模型移动到指定设备
    print(f"模型参数量: {sum(p.numel() for p in model.parameters() if p.requires_grad)}")

    print("模型初始化完成!")
    print("="*50)

    # 初始化训练器
    print("正在初始化训练器...")

    trainer = WandBTrainer(args, model, train_loader, test_loader, verbose=True)
    print("训练器初始化完成!")
    print("="*50)

    # 设置训练模式
    if args.is_training:
        # 开始训练
        print("开始训练模型...")
        best_metric,current_loss = trainer.train()

    else:
        # 加载最佳模型
        print("正在加载最佳模型...")
        model.load_state_dict(torch.load(args.save_path + '/model.pkl'))
        print("最佳模型加载完成!")
        print("="*50)

        # 开始测试
        print("开始测试模型...")
        trainer.eval_model_vqvae()
        print("模型测试完成!")
    

if __name__ == '__main__':
    # 设置随机种子
    print("="*50)
    print("正在设置随机种子...")
    seed_everything(seed=2024)
    print("随机种子设置完成!")
    print("="*50)

    args.pred_len = 0 # for classification
    args.label_len = 1

    # 使用wandb的sweep功能进行超参数调整
    sweep_config = {
        "name": f"{args.model}-{args.dataset_name}-sweep",
        "method": "bayes",
        'metric': {
        'goal': 'maximize', 
        'name': 'accuracy'
        },
        "parameters": {
            "lr":{"values":[0.01,0.001]},
            "batch_size":{"values": [16,32,64]},
            "e_layers": {"values": [3]},
            "d_model": {"values": [16, 32, 64]},
            "d_ff": {"values": [16, 32, 64]},
            # "embed": {"values": ['fixed', 'timeF']},
            "top_k": {"values": [3]},
            "dropout": {"values": [0.2]},
        },
        "early_terminate": {
        "type": "hyperband",
        "min_iter": 2
        }
    }

    sweep_id = wandb.sweep(sweep_config, project=f"{args.model}-{args.dataset_name}-final")
    wandb.agent(sweep_id, train_wandb)

    # # 找出最佳实验
    # best_run = wandb.Api().runs(f"{args.model}-{args.dataset_name}", filters={"sweep": {"$in": [sweep_id]}}).best("accuracy")
    # # 打印最佳实验的参数配置
    # print("Best run config: {}".format(best_run.config))
    # print("Best run final validation loss: {}".format(
    #     best_run.summary["loss"]))
    # print("Best run final validation accuracy: {}".format(
    #     best_run.summary["accuracy"]))

