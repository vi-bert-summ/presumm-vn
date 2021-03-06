from torch.utils.data import DataLoader

from inp_dataloader.ext_summ_dataset import ExtSummDataset
from model_builder.ext_bert_summ_pylight import ExtBertSummPylight
from trainer.trainer_builder import start_training
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
    ap.add_argument('-load_checkpoint', '--load_checkpoint', required=False, help='Specify the checkpoint to load')

    args = vars(ap.parse_args())

    return args


if __name__ == '__main__':
    cmd_args = args_parser()

    phase = cmd_args.get('phase')

    if phase == 'train':
        train_dataset = ExtSummDataset(bert_data_folder_path=cmd_args.get('json_data'), phase=cmd_args.get('phase'))
        train_dataloader = DataLoader(dataset=train_dataset, batch_size=int(cmd_args.get('batch_size')), shuffle=True,
                                      num_workers=4)

        ext_bert_summ_pylight = ExtBertSummPylight()
        save_check_point_path = cmd_args.get('load_checkpoint')
        if save_check_point_path is not None:
            ext_bert_summ_pylight.load_from_checkpoint(save_check_point_path)

        val_dataset = ExtSummDataset(bert_data_folder_path=cmd_args.get('json_data'), phase='val')
        val_dataloader = DataLoader(dataset=val_dataset, batch_size=int(cmd_args.get('batch_size')), shuffle=False,
                                    num_workers=4)

        start_training(abs_bert_summ_model=ext_bert_summ_pylight, train_dataloader=train_dataloader,
                       val_dataloader=val_dataloader, gpus=cmd_args.get('gpus'),
                       save_ckpt_path=cmd_args.get('save_ckpt_path')
                       )
