import torch
from torch.nn.functional import one_hot
from pytorch_lightning import LightningModule
from transformers import AdamW, get_linear_schedule_with_warmup
from torch.nn import CrossEntropyLoss

from model_builder.abs_bert_summ import AbsBertSumm


class AbsBertSummPylight(LightningModule):

    def __init__(self, vocab_size
                 , tokenizer=None
                 , learning_rate: float = 2e-5
                 , adam_epsilon: float = 1e-8
                 , warmup_steps: int = 10000
                 , weight_decay: float = 0.01
                 , **kwargs):
        super().__init__()
        abs_bert_summ = AbsBertSumm(vocab_size=vocab_size, tokenizer=tokenizer)
        self.model = abs_bert_summ
        self.save_hyperparameters()
        self.total_steps = 10
        self.vocab_size = vocab_size
        self.loss_fn = CrossEntropyLoss()
        self.tokenizer = tokenizer

    def forward(self, src_inp_ids, src_tok_type_ids, src_lis_cls_pos, src_mask
                , tgt_inp_ids, tgt_tok_type_ids, tgt_lis_cls_pos, tgt_mask):
        return self.model(src_ids=src_inp_ids, src_pad_mask=src_mask, src_token_type=src_tok_type_ids
                          # , is_freeze_phase1=True
                          , src_cls_pos=src_lis_cls_pos
                          , tgt_ids=tgt_inp_ids, tgt_pad_mask=tgt_mask, tgt_token_type=tgt_tok_type_ids)

    def training_step(self, batch, batch_idx, optimizer_idx):
        """
        :param batch: input dataloader (src_inp_ids, src_tok_type_ids, src_lis_cls_pos, src_mask
                        , tgt_inp_ids, tgt_tok_type_ids, tgt_lis_cls_pos, tgt_mask)
        :param batch_idx: Số thứ tự của batch
        :param optimizer_idx: Số thứ tự của optimizer
        :return:
        """
        src_inp_ids, src_tok_type_ids, src_lis_cls_pos, src_mask, tgt_inp_ids \
            , tgt_tok_type_ids, tgt_lis_cls_pos, tgt_mask = batch
        logits = self.model(src_ids=src_inp_ids
                            , src_pad_mask=src_mask
                            , src_token_type=src_tok_type_ids
                            , src_cls_pos=src_lis_cls_pos
                            , tgt_ids=tgt_inp_ids
                            , tgt_pad_mask=tgt_mask
                            , tgt_token_type=tgt_tok_type_ids)
        out_prob = torch.softmax(logits, dim=2)
        tgt_one_hot = one_hot(tgt_inp_ids, num_classes=self.vocab_size)

        loss = None
        for item_id in range(len(out_prob)):
            num_used_token = tgt_mask[item_id].sum()
            used_prob = out_prob[item_id][:num_used_token]
            used_tgt_one_hot = tgt_one_hot[item_id][:num_used_token]
            single_loss = self.loss_fn(used_prob, used_tgt_one_hot.float())
            if loss is None:
                loss = single_loss
            else:
                loss += single_loss

        tensorboard_logs = {'train_loss': loss.detach()}
        return {'loss': loss, 'log': tensorboard_logs}

    def validation_step(self, batch, batch_idx):
        src_inp_ids, src_tok_type_ids, src_lis_cls_pos, src_mask, tgt_inp_ids \
            , tgt_tok_type_ids, tgt_lis_cls_pos, tgt_mask = batch
        with torch.no_grad():
            logits = self.model(src_ids=src_inp_ids, src_pad_mask=src_mask, src_token_type=src_tok_type_ids
                                # , is_freeze_phase1=True
                                , src_cls_pos=src_lis_cls_pos
                                , tgt_ids=tgt_inp_ids
                                , tgt_pad_mask=tgt_mask
                                , tgt_token_type=tgt_tok_type_ids)
            out_prob = torch.softmax(logits, dim=2)
            tgt_one_hot = one_hot(tgt_inp_ids, num_classes=self.vocab_size)

            loss = None
            for item_id in range(len(out_prob)):
                num_used_token = tgt_mask[item_id].sum()
                used_prob = out_prob[item_id][:num_used_token]
                used_tgt_one_hot = tgt_one_hot[item_id][:num_used_token]
                single_loss = self.loss_fn(used_prob, used_tgt_one_hot.float())
                if loss is None:
                    loss = single_loss
                else:
                    loss += single_loss

            tensorboard_logs = {'val_loss': loss}
            self.log('val_loss', loss)
            return {'loss': loss, 'log': tensorboard_logs}

    def predict_step(self, batch, batch_idx, dataloader_idx=None):
        src_inp_ids, src_tok_type_ids, src_lis_cls_pos, src_mask, tgt_inp_ids \
            , tgt_tok_type_ids, tgt_lis_cls_pos, tgt_mask = batch
        with torch.no_grad():
            logits = self.model(src_ids=src_inp_ids, src_pad_mask=src_mask, src_token_type=src_tok_type_ids
                                # , is_freeze_phase1=True
                                , src_cls_pos=src_lis_cls_pos
                                , tgt_ids=tgt_inp_ids
                                , tgt_pad_mask=tgt_mask
                                , tgt_token_type=tgt_tok_type_ids)
            out_prob = torch.softmax(logits, dim=2)
            out_ids = torch.argmax(out_prob, dim=2)

            lis_res = []
            for each_batch in out_ids:
                lis_res.append(self.tokenizer.phobert_tokenizer.decode(each_batch))
            return lis_res

    def configure_optimizers(self):
        """
        Chuẩn bị Optimizer với chiến lược warm-up và weight-decay
        """
        model = self.model
        no_decay = ["bias", "LayerNorm.weight"]
        phase1_name = ['phase1_bert']
        phase2_name = ['phase2_trans_decoder']

        named_params = model.named_parameters()

        optimizer_grouped_parameters_phase1 = [
            {
                "params": [p for n, p in named_params if
                           not any(nd in n for nd in no_decay) and any(p1 in n for p1 in phase1_name)],
                "weight_decay": self.hparams.weight_decay,
            },
            {
                "params": [p for n, p in named_params if
                           any(nd in n for nd in no_decay) and any(p1 in n for p1 in phase1_name)],
                "weight_decay": 0.0,
            }
        ]

        optimizer_grouped_parameters_phase2 = [
            {
                "params": [p for n, p in named_params if
                           not any(nd in n for nd in no_decay) and any(p1 in n for p1 in phase2_name)],
                "weight_decay": self.hparams.weight_decay,
            },
            {
                "params": [p for n, p in named_params if
                           any(nd in n for nd in no_decay) and any(p2 in n for p2 in phase2_name)],
                "weight_decay": 0.0,
            }
        ]

        optimizer_phase1 = AdamW(params=optimizer_grouped_parameters_phase1,
                                 lr=2e-3,
                                 eps=1e-8,
                                 betas=[0.9, 0.999])

        optimizer_phase2 = AdamW(params=optimizer_grouped_parameters_phase2,
                                 lr=0.1,
                                 eps=1e-8,
                                 betas=[0.9, 0.999])

        scheduler_phase1 = get_linear_schedule_with_warmup(
            optimizer_phase1,
            num_warmup_steps=20000,
            num_training_steps=self.total_steps,
        )

        scheduler_phase2 = get_linear_schedule_with_warmup(
            optimizer_phase2,
            num_warmup_steps=10000,
            num_training_steps=self.total_steps,
        )

        scheduler_phase1 = {"scheduler": scheduler_phase1, "interval": "step", "frequency": 1}

        return [optimizer_phase1, optimizer_phase2], [scheduler_phase1, scheduler_phase2]
