package com.velo.vpn.ui.screens

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavHostController
import com.velo.vpn.ui.AccountViewModel
import com.velo.vpn.ui.CommerceViewModel
import com.velo.vpn.ui.Routes
import com.velo.vpn.ui.components.PrimaryButton
import com.velo.vpn.ui.components.VeloCard
import com.velo.vpn.ui.components.VeloHeader
import com.velo.vpn.ui.theme.HeartPink
import com.velo.vpn.ui.theme.Muted
import com.velo.vpn.ui.theme.VeloPurple

@Composable
fun ManualPaymentScreen(
    nav: NavHostController,
    kind: String,
    planCode: String?,
    baseAmount: Int,
    commerce: CommerceViewModel,
    account: AccountViewModel,
) {
    val context = LocalContext.current
    val commerceState by commerce.state.collectAsState()
    val accountState by account.state.collectAsState()
    val config = commerceState.config
    var receiptUri by remember { mutableStateOf<Uri?>(null) }
    var requestedHearts by remember { mutableIntStateOf(0) }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        receiptUri = uri
        if (uri != null) runCatching { context.contentResolver.takePersistableUriPermission(uri, android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION) }
    }

    val discountTiers = config?.heartDiscountTiers.orEmpty()
        .mapNotNull { (h, p) -> h.toIntOrNull()?.let { it to p } }
        .filter { (h, p) -> h <= accountState.hearts && p <= (config?.maxHeartDiscountPercent ?: 30) }
        .sortedBy { it.first }
    val discountPercent = discountTiers.firstOrNull { it.first == requestedHearts }?.second ?: 0
    val finalAmount = if (kind == "premium") {
        ((baseAmount.toLong() * (100 - discountPercent) + 99) / 100).toInt()
    } else baseAmount
    val supportHearts = config?.supportHeartTiers?.get(baseAmount.toString())

    Scaffold { pad ->
        Column(
            Modifier.fillMaxSize().padding(pad).verticalScroll(rememberScrollState()).padding(18.dp),
            verticalArrangement = Arrangement.spacedBy(13.dp),
        ) {
            VeloHeader(showBack = true, hearts = accountState.hearts, onBack = { nav.popBackStack() })
            Text(if (kind == "premium") "پرداخت اشتراک" else "پرداخت حمایت", fontSize = 30.sp, fontWeight = FontWeight.ExtraBold)

            if (!accountState.loggedIn) {
                VeloCard(Modifier.fillMaxWidth()) {
                    Text("برای اینکه پرداخت و هدیه‌های شما محفوظ بماند، ابتدا با ایمیل وارد حساب Velo شوید.", fontWeight = FontWeight.Bold)
                    Spacer(Modifier.height(12.dp))
                    PrimaryButton("ورود با ایمیل") { nav.navigate(Routes.Account) }
                }
                return@Column
            }

            VeloCard(Modifier.fillMaxWidth()) {
                Text("مبلغ", color = Muted)
                Text("%,d تومان".format(finalAmount), fontSize = 24.sp, fontWeight = FontWeight.Bold)
                if (kind == "premium" && requestedHearts > 0) {
                    Text("تخفیف $discountPercent٪ با $requestedHearts قلب", color = HeartPink, fontSize = 12.sp)
                } else if (kind == "support" && supportHearts != null) {
                    Text("پس از تایید: +$supportHearts قلب", color = HeartPink, fontSize = 12.sp)
                }
            }

            if (kind == "premium" && discountTiers.isNotEmpty()) {
                VeloCard(Modifier.fillMaxWidth()) {
                    Text("استفاده از قلب‌ها", fontWeight = FontWeight.Bold)
                    Text("هر خرید فقط یک سطح تخفیف دارد و سقف تخفیف حفظ می‌شود.", color = Muted, fontSize = 11.sp)
                    Spacer(Modifier.height(8.dp))
                    Row(
                        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(7.dp),
                    ) {
                        FilterChip(selected = requestedHearts == 0, onClick = { requestedHearts = 0 }, label = { Text("بدون تخفیف") })
                        discountTiers.forEach { (hearts, percent) ->
                            FilterChip(
                                selected = requestedHearts == hearts,
                                onClick = { requestedHearts = hearts },
                                label = { Text("$percent٪ • $hearts ♥") },
                            )
                        }
                    }
                }
            }

            VeloCard(Modifier.fillMaxWidth()) {
                Text("کارت‌به‌کارت", fontWeight = FontWeight.Bold)
                Spacer(Modifier.height(10.dp))
                Text(config?.manualCardNumber ?: "—", fontSize = 20.sp, fontWeight = FontWeight.Bold)
                Text(config?.manualCardHolder ?: "Velo", color = Muted, fontSize = 12.sp)
                Spacer(Modifier.height(10.dp))
                OutlinedButton(onClick = {
                    val card = config?.manualCardNumber.orEmpty()
                    if (card.isNotBlank()) {
                        val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                        clipboard.setPrimaryClip(ClipData.newPlainText("Velo card", card))
                    }
                }) {
                    Icon(Icons.Default.ContentCopy, null)
                    Spacer(Modifier.width(6.dp))
                    Text("کپی شماره کارت")
                }
            }

            VeloCard(Modifier.fillMaxWidth()) {
                Text("ارسال فیش", fontWeight = FontWeight.Bold)
                Text("بعد از انتقال وجه، تصویر یا PDF رسید را انتخاب کنید.", color = Muted, fontSize = 12.sp)
                Spacer(Modifier.height(10.dp))
                OutlinedButton(onClick = { picker.launch(arrayOf("image/jpeg", "image/png", "image/webp", "application/pdf")) }) {
                    Text(if (receiptUri == null) "انتخاب فیش" else "فیش انتخاب شد ✓")
                }
            }

            PrimaryButton(if (commerceState.submitting) "در حال ارسال…" else "ارسال برای بررسی") {
                val uri = receiptUri
                if (uri != null && !commerceState.submitting && finalAmount > 0) {
                    commerce.submit(
                        context = context,
                        uri = uri,
                        kind = kind,
                        amountToman = finalAmount,
                        planCode = planCode,
                        requestedHearts = if (kind == "premium") requestedHearts else 0,
                    )
                }
            }
            commerceState.pendingPaymentId?.let {
                Text("درخواست #$it ثبت شد و در انتظار بررسی ادمین است.", color = VeloPurple, fontWeight = FontWeight.Bold)
            }
            commerceState.error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            commerceState.info?.let { Text(it, color = VeloPurple) }
            Text("فعال‌سازی یا اضافه‌شدن قلب‌ها پس از بررسی پرداخت انجام می‌شود.", color = Muted, fontSize = 11.sp)
        }
    }
}
