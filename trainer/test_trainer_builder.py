from pytorch_lightning import Trainer
from torch.utils.data import DataLoader

from inp_dataloader.summ_dataset import SummDataset
from model_builder.abs_bert_summ import AbsBertSumm
from model_builder.abs_bert_summ_pylight import AbsBertSummPylight
from tokenize_input.summ_tokenize import SummTokenize
from trainer.trainer_builder import start_training, start_test
import argparse


def args_parser():
    # Construct the argument parser
    ap = argparse.ArgumentParser()

    # Add the arguments to the parser
    ap.add_argument('-jsondat', '--json_data', required=True, help='Input in json format')
    ap.add_argument('-gpus', '--gpus', required=False, help='Specify gpus device')
    ap.add_argument('-phase', '--phase', required=False, help='Specify phase [train, val, test]')
    ap.add_argument('-batch_size', '--batch_size', required=False, help='Specify the batch size')
    ap.add_argument('-save_ckpt_path', '--save_ckpt_path', required=False, help='Specify the checkpoint path')
    # -jsondat /Users/LongNH/Workspace/data/abs_bert_data -gpus -1 -phase test -batch_size 4 -save_ckpt_path /Users/LongNH/Workspace/data/lightning_logs/version3/checkpoints/epoch=0-step=13177.ckpt
    args = vars(ap.parse_args())

    return args


if __name__ == '__main__':
    cmd_args = args_parser()
    phase = cmd_args.get('phase')
    tokenizer = SummTokenize()
    vocab_size = tokenizer.phobert_tokenizer.vocab_size

    if phase == 'train':

        train_dataset = SummDataset(bert_data_folder_path=cmd_args.get('json_data'), phase=cmd_args.get('phase'))
        train_dataloader = DataLoader(dataset=train_dataset, batch_size=int(cmd_args.get('batch_size')), shuffle=True,
                                      num_workers=4)

        abs_bert_summ_pylight = AbsBertSummPylight(vocab_size=vocab_size)
        save_check_point_path = cmd_args.get('save_ckpt_path')
        if save_check_point_path is not None:
            abs_bert_summ_pylight.load_from_checkpoint(save_check_point_path)

        val_dataset = SummDataset(bert_data_folder_path=cmd_args.get('json_data'), phase='val')
        val_dataloader = DataLoader(dataset=val_dataset, batch_size=int(cmd_args.get('batch_size')), shuffle=False,
                                    num_workers=4)

        start_training(abs_bert_summ_model=abs_bert_summ_pylight, train_dataloader=train_dataloader,
                       val_dataloader=val_dataloader, gpus=cmd_args.get('gpus'),
                       save_ckpt_path=cmd_args.get('save_ckpt_path')
                       )

    elif phase == 'test':
        test_dataset = SummDataset(bert_data_folder_path=cmd_args.get('json_data'), phase=cmd_args.get('phase'))
        test_dataloader = DataLoader(dataset=test_dataset, batch_size=int(cmd_args.get('batch_size')), shuffle=False,
                                     num_workers=4)
        abs_bert_summ_pylight = AbsBertSummPylight(vocab_size=vocab_size, tokenizer=tokenizer)
        abs_bert_summ_pylight.load_from_checkpoint(cmd_args.get('save_ckpt_path'))
        start_test(model=abs_bert_summ_pylight, test_dataloader=test_dataloader, gpus=cmd_args.get('gpus'))
